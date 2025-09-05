from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import os, httpx, hashlib

from .db import get_session
from .redis_kv import acquire_once
from .queries import fetch_order_by_id, fetch_order_items, fetch_order_tags

# === Config ===
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
WEBHOOK_SECRET = os.getenv("MCP_WEBHOOK_SECRET", "changeme")

# Prompt base configurable (fallback seguro si no está en .env)
BASE_ANALYZE_PROMPT = os.getenv(
    "ANALYZE_PROMPT",
    (
        "Eres un asistente MCP de integraciones. Analiza la orden y responde en español, "
        "breve y claro: (1) si los totales parecen coherentes con las líneas, "
        "(2) campos críticos que faltan para Odoo/Zoho (NIT, dirección, SKU, qty>0), "
        "(3) alertas de riesgo (voided, estado de pago/envío), (4) sugerencia de acción."
    ),
)

app = FastAPI(title="MCP Orchestrator")

# === Util ===
async def ollama_generate(prompt: str, model: str | None = None) -> str:
    mdl = model or OLLAMA_MODEL
    url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate"
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(url, json={"model": mdl, "prompt": prompt})
        r.raise_for_status()
        data = r.json()
    return data.get("response", "")

# === Endpoints ===
@app.get("/health")
def health():
    return {"ok": True, "ollama": f"http://{OLLAMA_HOST}:{OLLAMA_PORT}", "model": OLLAMA_MODEL}

@app.post("/llm/complete")
async def llm_complete(body: dict):
    """
    body: { "prompt": "...", "model": "opcional" }
    """
    prompt = body.get("prompt")
    if not prompt:
        raise HTTPException(status_code=400, detail="Falta prompt")
    model = body.get("model", OLLAMA_MODEL)
    try:
        response = await ollama_generate(prompt, model=model)
        return {"ok": True, "model": model, "response": response}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e}")

@app.post("/webhooks/order_paid")
async def order_paid(payload: dict, db: Session = Depends(get_session)):
    """
    Espera: {"secret":"...", "source":"laravel-core","order_id":123}
    """
    if payload.get("secret") != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="unauthorized")

    try:
        order_id = int(payload["order_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="order_id inválido")

    source = payload.get("source", "laravel-core")

    # Idempotencia por 1h
    key = "idempo:" + hashlib.sha256(f"{source}:{order_id}".encode()).hexdigest()
    if not acquire_once(key, ttl_sec=3600):
        return {"ok": True, "status": "duplicate_ignored"}

    order = fetch_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")

    # Aquí: validaciones + transformaciones + envíos (Odoo/Zoho)
    return {"ok": True, "order": dict(order)}

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
    )

    model = body.get("model")  # si None, usa OLLAMA_MODEL
    try:
        analysis = await ollama_generate(prompt, model=model)
        return {"ok": True, "order_id": order_id, "analysis": analysis}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e}")
