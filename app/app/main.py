from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import os, httpx, hashlib

from .db import get_session
from .redis_kv import acquire_once
from .queries import fetch_order_by_id, fetch_order_items, fetch_order_tags
from .validate import validate_items_present, validate_basic_totals, validate_customer, ValidationError
from .transform import build_odoo_invoice, build_zoho_sales_order
# from .models import OdooInvoice, ZohoSalesOrder  # se usan en los mocks (lo dejamos)
from .models import OdooInvoice, ZohoSalesOrder

SINK_ODOO_URL = os.getenv("SINK_ODOO_URL", "http://127.0.0.1:8080/mock/odoo/invoices")
SINK_ZOHO_URL = os.getenv("SINK_ZOHO_URL", "http://127.0.0.1:8080/mock/zoho/salesorders")

# === Config ===
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
WEBHOOK_SECRET = os.getenv("MCP_WEBHOOK_SECRET", "changeme")

BASE_ANALYZE_PROMPT = os.getenv(
    "ANALYZE_PROMPT",
    ("Eres un asistente MCP de integraciones. Analiza la orden y responde en español, "
     "breve y claro: (1) si los totales parecen coherentes con las líneas, "
     "(2) campos críticos que faltan para Odoo/Zoho (NIT, dirección, SKU, qty>0), "
     "(3) alertas de riesgo (voided, estado de pago/envío), (4) sugerencia de acción.")
)

app = FastAPI(title="MCP Orchestrator")

# === Util ===
async def ollama_generate(prompt: str, model: str | None = None) -> str:
    mdl = model or OLLAMA_MODEL
    url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate"
    payload = {"model": mdl, "prompt": prompt, "stream": False}
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
    return data.get("response", "")

# === Endpoints ===
@app.post("/webhooks/order_paid")
async def order_paid(payload: dict, db: Session = Depends(get_session)):
    if payload.get("secret") != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="unauthorized")

    try:
        order_id = int(payload["order_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="order_id inválido")

    source = payload.get("source", "laravel-core")

    # Idempotencia 1h
    key = "idempo:" + hashlib.sha256(f"{source}:{order_id}".encode()).hexdigest()
    if not acquire_once(key, ttl_sec=3600):
        return {"ok": True, "status": "duplicate_ignored"}

    order = fetch_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")

    # --- actualizar estado a pagada (DEDENTADO) ---
    paid_id = int(os.getenv("PAID_STATUS_ID", "2"))
    db.execute(
        text("UPDATE orders SET status_payment_id = :paid WHERE id = :id"),
        {"paid": paid_id, "id": order_id}
    )
    # log opcional (no fallar si no existe la tabla)
    try:
        db.execute(
            text("INSERT INTO integration_logs (order_id, system, status, message) "
                 "VALUES (:id,'mcp','info','order_paid processed')"),
            {"id": order_id}
        )
    except Exception:
        pass
    db.commit()

    # Releer orden + items
    order = fetch_order_by_id(db, order_id)
    items = fetch_order_items(db, order_id)

    # Validaciones mínimas
    try:
        validate_items_present(items)
        validate_customer(order)
        validate_basic_totals(order, items)
    except ValidationError as ve:
        return {"ok": False, "error": str(ve), "order": dict(order), "items": [dict(i) for i in items]}

    # Transformaciones
    org_id = os.getenv("ORG_ID_ZOHO", "")
    odoo_payload = build_odoo_invoice(order, items)
    zoho_payload = build_zoho_sales_order(order, items, org_id)

    return {
        "ok": True,
        "status_payment_id": order.get("status_payment_id"),
        "odoo_invoice": odoo_payload,
        "zoho_sales_order": zoho_payload
    }

@app.post("/orders/send_mock")
async def send_order_to_mocks(body: dict, db: Session = Depends(get_session)):
    order_id = body.get("order_id")
    if not order_id:
        raise HTTPException(status_code=400, detail="Falta order_id")
    order_id = int(order_id)

    order = fetch_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    items = fetch_order_items(db, order_id)

    try:
        validate_items_present(items)
        validate_customer(order)
        validate_basic_totals(order, items)
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    odoo_payload = build_odoo_invoice(order, items)
    zoho_payload = build_zoho_sales_order(order, items, os.getenv("ORG_ID_ZOHO",""))

    async with httpx.AsyncClient(timeout=30) as c:
        odoo_res = await c.post(SINK_ODOO_URL, json=odoo_payload)
        zoho_res = await c.post(SINK_ZOHO_URL, json=zoho_payload)
        odoo_res.raise_for_status()
        zoho_res.raise_for_status()
        odoo_data = odoo_res.json()
        zoho_data = zoho_res.json()

    return {"ok": True, "order_id": order_id, "odoo_result": odoo_data, "zoho_result": zoho_data}

@app.post("/orders/analyze")
async def analyze_order(body: dict, db: Session = Depends(get_session)):
    """
    body:
      {
        "order_id": 1024,
        "prompt": "opcional (sobrescribe el prompt base)",
        "model": "opcional (modelo ollama)"
      }
    """
    order_id = body.get("order_id")
    if order_id is None:
        raise HTTPException(status_code=400, detail="Falta order_id")

    try:
        order_id = int(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="order_id inválido")

    order = fetch_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")

    items = fetch_order_items(db, order_id)
    tags  = fetch_order_tags(db, order_id)
    
    subtotal_total = sum([x["subtotal"] for x in items])
    diff = float(order["total"]) - float(subtotal_total)


    # 1) Prompt base desde .env
    base = BASE_ANALYZE_PROMPT.strip()

    # 2) Permitir override desde el request (si viene 'prompt')
    override = (body.get("prompt") or "").strip()
    head = override if override else base

    prompt = (
        f"{head}\n\n"
        f"ORDER: {dict(order)}\n"
        f"ITEMS: {[dict(x) for x in items]}\n"
        f"TAGS: {tags}\n"
        f"\nNota: El subtotal de los items es {subtotal_total}, "
        f"el total de la orden es {order['total']}, diferencia={diff}.\n"
    )
    print(f"[order items] prompt: {prompt}")
    model = body.get("model")  # si None, usa OLLAMA_MODEL
    try:
        analysis = await ollama_generate(prompt, model=model)
        return {"ok": True, "order_id": order_id, "analysis": analysis}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e}")


@app.post("/orders/transform")
def transform_order(body: dict, db: Session = Depends(get_session)):
    """
    Transforma una orden a los payloads requeridos por Odoo y Zoho, sin enviarlos.
    body:
      {
        "order_id": 1
      }
    """
    order_id = body.get("order_id")
    if not order_id:
        raise HTTPException(status_code=400, detail="Falta order_id")

    order = fetch_order_by_id(db, int(order_id))
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")

    items = fetch_order_items(db, int(order_id))

    # Validaciones mínimas antes de transformar
    try:
        validate_items_present(items)
        validate_customer(order)
        validate_basic_totals(order, items)
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    # Construir payloads
    odoo_payload = build_odoo_invoice(order, items)
    zoho_payload = build_zoho_sales_order(order, items, os.getenv("ORG_ID_ZOHO", ""))

    return {
        "ok": True,
        "order_id": int(order_id),
        "odoo": odoo_payload,
        "zoho": zoho_payload
    }



@app.post("/mock/odoo/invoices")
def mock_odoo_invoices(payload: OdooInvoice):
    """
    Simula receptor de Odoo: valida el JSON y responde un ID ficticio.
    """
    if not payload.invoice_ref:
        raise HTTPException(status_code=400, detail="invoice_ref requerido")

    inv_id = f"INV-{payload.invoice_ref}"
    return {
        "ok": True,
        "invoice_id": inv_id,
        "received_lines": len(payload.invoice_lines)
    }

@app.post("/mock/zoho/salesorders")
def mock_zoho_salesorders(payload: ZohoSalesOrder):
    """
    Simula receptor de Zoho: valida el JSON y responde un ID ficticio.
    """
    if not payload.reference_number:
        raise HTTPException(status_code=400, detail="reference_number requerido")

    so_id = f"SO-{payload.reference_number}"
    return {
        "ok": True,
        "salesorder_id": so_id,
        "received_lines": len(payload.line_items)
    }