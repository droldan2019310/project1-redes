# app/app/mcp_server.py
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from decimal import Decimal
import os, json, httpx, hashlib
from .sessions import create_session, append_message, get_history

# ====== CONFIG ======
PROTOCOL_VERSION = "2024-09"
SERVER_NAME = "mcp-orchestrator"
SERVER_VERSION = "0.1.0"

# Relee las mismas vars de entorno que usas en main.py
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
WEBHOOK_SECRET = os.getenv("MCP_WEBHOOK_SECRET", "changeme")
PAID_STATUS_ID = int(os.getenv("PAID_STATUS_ID", "2"))
SINK_ODOO_URL = os.getenv("SINK_ODOO_URL", "http://127.0.0.1:8080/mock/odoo/invoices")
SINK_ZOHO_URL = os.getenv("SINK_ZOHO_URL", "http://127.0.0.1:8080/mock/zoho/salesorders")

BASE_ANALYZE_PROMPT = os.getenv(
    "ANALYZE_PROMPT",
    (
        "Eres un asistente MCP de integraciones. Analiza la orden y responde en español, "
        "breve y claro: (1) si los totales parecen coherentes con las líneas, "
        "(2) campos críticos que faltan para Odoo/Zoho (NIT, dirección, SKU, qty>0), "
        "(3) alertas de riesgo (voided, estado de pago/envío), (4) sugerencia de acción."
    ),
)

# ====== IMPORTS DE TU CÓDIGO ======
from .db import get_session
from .queries import fetch_order_by_id, fetch_order_items, fetch_order_tags
from .validate import (
    validate_items_present, validate_basic_totals, validate_customer, ValidationError
)
from .transform import build_odoo_invoice, build_zoho_sales_order

# ====== ROUTER MCP ======
mcp = APIRouter()

TOOLS = [
    {
        "name": "orders.analyze",
        "description": "Analiza una orden con LLM",
        "inputSchema": {
            "type": "object",
            "required": ["order_id"],
            "properties": {
                "order_id": {"type": "integer"},
                "prompt": {"type": "string"},
                "model": {"type": "string"},
                "session_id": {"type": "integer"}  
            }
        }
    },
    {
        "name": "orders.transform",
        "description": "Convierte la orden a payloads Odoo/Zoho (no los envía)",
        "inputSchema": {
            "type": "object",
            "required": ["order_id"],
            "properties": {
                "order_id": {"type": "integer"},
                "session_id": {"type": "integer"}  

            }
        }
    },
    {
        "name": "orders.send_mock",
        "description": "Genera y envía payloads a los endpoints mock (Odoo/Zoho)",
        "inputSchema": {
            "type": "object",
            "required": ["order_id"],
            "properties": {"order_id": {"type": "integer"},            
                            "session_id": {"type": "integer"} 
            }
        }
    },
    {
        "name": "webhooks.order_paid",
        "description": "Marca como pagada, valida y prepara payloads",
        "inputSchema": {
            "type": "object",
            "required": ["order_id", "secret"],
            "properties": {
                "order_id": {"type": "integer"},
                "secret":   {"type": "string"},
                "source":   {"type": "string"},
                "session_id": {"type": "integer"} 
            }
        }
    },
    {
        "name": "sessions.create",
        "description": "Crea una nueva sesión y devuelve session_id",
        "inputSchema": {
            "type": "object",
            "properties": { "title": {"type":"string"} }
        }
    },
    {
        "name": "sessions.get_history",
        "description": "Devuelve el historial de una sesión",
        "inputSchema": {
            "type": "object",
            "required": ["session_id"],
            "properties": { "session_id": {"type":"integer"} }
        }
    },
]

# ====== JSON-RPC helpers ======
def make_result(_id, result): 
    return {"jsonrpc": "2.0", "id": _id, "result": result}

def make_error(_id, code, message, data=None):
    err = {"jsonrpc": "2.0", "id": _id, "error": {"code": code, "message": message}}
    if data is not None:
        err["error"]["data"] = data
    return err

# ====== Ollama helper (igual que en main, para evitar import circular) ======
async def ollama_generate(prompt: str, model: str | None = None) -> str:
    mdl = model or OLLAMA_MODEL
    url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate"
    payload = {"model": mdl, "prompt": prompt, "stream": False}
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
    return data.get("response", "")


def _db() -> Session:
    # get_session() es un generator (yield); aquí obtenemos una sesión usable
    return next(get_session())

async def _call_analyze(args: dict):
    order_id = int(args.get("order_id"))
    override = (args.get("prompt") or "").strip()
    model = args.get("model")
    session_id = args.get("session_id") 

    db = _db()
    order = fetch_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    items = fetch_order_items(db, order_id)
    tags  = fetch_order_tags(db, order_id)

    head = override if override else BASE_ANALYZE_PROMPT.strip()

    subtotal_total = float(sum([float(i.get("subtotal", 0)) for i in items]))
    total_order = float(order.get("total") or 0)
    diff = round(total_order - subtotal_total, 2)

    prompt = (
        f"{head}\n\n"
        f"ORDER: {dict(order)}\n"
        f"ITEMS: {[dict(x) for x in items]}\n"
        f"TAGS: {tags}\n"
        f"\nResumen numérico:\n"
        f"- Subtotal items: {subtotal_total}\n"
        f"- Total orden: {total_order}\n"
        f"- Diferencia: {diff}\n"
        f"Explica si cuadran o no y sugiere la siguiente acción.\n"
    )

    if session_id:
        append_message(db, int(session_id), "user", {
            "tool": "orders.analyze",
            "args": {"order_id": order_id, "prompt": override, "model": model},
            "computed": {"subtotal_items": subtotal_total, "total_order": total_order, "diff": diff},
            "prompt_to_llm": prompt
        })

    analysis = await ollama_generate(prompt, model=model)

    if session_id:
        append_message(db, int(session_id), "assistant", {
            "tool": "orders.analyze",
            "result_text": analysis
        })

    return {
        "ok": True,
        "order_id": order_id,
        "calc": {
            "subtotal_items": subtotal_total,
            "total_order": total_order,
            "difference": diff,
            "matches": abs(diff) < 0.01
        },
        "analysis": analysis,
        "session_id": int(session_id) if session_id else None
    }


async def _call_transform(args: dict):
    order_id = int(args.get("order_id"))
    session_id = args.get("session_id")  

    db = _db()
    order = fetch_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    items = fetch_order_items(db, order_id)

    validate_items_present(items)
    validate_customer(order)
    validate_basic_totals(order, items)

    odoo_payload = build_odoo_invoice(order, items)
    zoho_payload = build_zoho_sales_order(order, items, os.getenv("ORG_ID_ZOHO",""))

    if session_id:
        append_message(db, int(session_id), "tool", {
            "tool": "orders.transform",
            "args": {"order_id": order_id},
            "output": {"odoo": odoo_payload, "zoho": zoho_payload}
        })

    return {"ok": True, "order_id": order_id, "odoo": odoo_payload, "zoho": zoho_payload, "session_id": int(session_id) if session_id else None}

async def _call_send_mock(args: dict):
    order_id = int(args.get("order_id"))
    session_id = args.get("session_id") 

    db = _db()
    order = fetch_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    items = fetch_order_items(db, order_id)

    validate_items_present(items)
    validate_customer(order)
    validate_basic_totals(order, items)

    odoo_payload = build_odoo_invoice(order, items)
    zoho_payload = build_zoho_sales_order(order, items, os.getenv("ORG_ID_ZOHO",""))

    async with httpx.AsyncClient(timeout=30) as c:
        odoo_res = await c.post(SINK_ODOO_URL, json=odoo_payload)
        zoho_res = await c.post(SINK_ZOHO_URL, json=zoho_payload)
        odoo_res.raise_for_status()
        zoho_res.raise_for_status()
        odoo_data = odoo_res.json()
        zoho_data = zoho_res.json()

    if session_id:
        append_message(db, int(session_id), "tool", {
            "tool": "orders.send_mock",
            "args": {"order_id": order_id},
            "payloads": {"odoo": odoo_payload, "zoho": zoho_payload},
            "results": {"odoo_result": odoo_data, "zoho_result": zoho_data}
        })

    return {
        "ok": True, "order_id": order_id,
        "odoo_result": odoo_data, "zoho_result": zoho_data,
        "session_id": int(session_id) if session_id else None
    }

async def _call_order_paid(args: dict):
    secret = args.get("secret")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="unauthorized")

    order_id = int(args.get("order_id"))
    source = args.get("source", "mcp-tool")
    session_id = args.get("session_id")  # <-- nuevo

    db = _db()
    order = fetch_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")

    # log user: intención de marcar pagado
    if session_id:
        append_message(db, int(session_id), "user", {
            "tool": "webhooks.order_paid",
            "args": {"order_id": order_id, "source": source}
        })

    db.execute(
        text("UPDATE orders SET status_payment_id = :paid WHERE id = :id"),
        {"paid": PAID_STATUS_ID, "id": order_id}
    )
    db.commit()

    order = fetch_order_by_id(db, order_id)
    items = fetch_order_items(db, order_id)

    try:
        validate_items_present(items)
        validate_customer(order)
        validate_basic_totals(order, items)
    except ValidationError as ve:
        if session_id:
            append_message(db, int(session_id), "assistant", {
                "tool": "webhooks.order_paid",
                "result": {"ok": False, "error": str(ve)}
            })
        return {"ok": False, "error": str(ve), "order": dict(order), "items": [dict(i) for i in items], "session_id": int(session_id) if session_id else None}

    odoo_payload = build_odoo_invoice(order, items)
    zoho_payload = build_zoho_sales_order(order, items, os.getenv("ORG_ID_ZOHO",""))
    result = {
        "ok": True,
        "status_payment_id": order.get("status_payment_id"),
        "odoo_invoice": odoo_payload,
        "zoho_sales_order": zoho_payload
    }

    # log assistant: resultado
    if session_id:
        append_message(db, int(session_id), "assistant", {
            "tool": "webhooks.order_paid",
            "result": result
        })

    return {**result, "session_id": int(session_id) if session_id else None}



async def _call_sessions_create(args: dict):
    title = (args.get("title") or "").strip()
    db = _db()
    sid = create_session(db, title or None)
    return {"ok": True, "session_id": sid, "title": title or None}

async def _call_sessions_get_history(args: dict):
    sid = int(args.get("session_id"))
    db = _db()
    hist = get_history(db, sid, limit=200)
    return {"ok": True, "session_id": sid, "messages": hist}

# ====== Punto único JSON-RPC sobre HTTP ======
@mcp.post("/mcp")
async def mcp_http(body: dict):
    if body.get("jsonrpc") != "2.0" or "method" not in body:
        return make_error(body.get("id"), -32600, "Invalid Request")

    method = body["method"]
    params = body.get("params") or {}
    _id = body.get("id")

    try:
        if method == "initialize":
            return make_result(_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": True, "resources": False, "prompts": False},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}
            })

        if method == "tools/list":
            return make_result(_id, {"tools": TOOLS})

        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            if name == "orders.analyze":
                return make_result(_id, await _call_analyze(args))
            if name == "orders.transform":
                return make_result(_id, await _call_transform(args))
            if name == "orders.send_mock":
                return make_result(_id, await _call_send_mock(args))
            if name == "webhooks.order_paid":
                return make_result(_id, await _call_order_paid(args))
            if name == "sessions.create":
                return make_result(_id, await _call_sessions_create(args))
            if name == "sessions.get_history":
                return make_result(_id, await _call_sessions_get_history(args))
            return make_error(_id, -32601, f"Method not found: {name}")

        return make_error(_id, -32601, f"Unknown method: {method}")

    except HTTPException as he:
        # Mapea errores HTTP a JSON-RPC estándar
        return make_error(_id, -32000, "Internal MCP error", {"status": he.status_code, "detail": he.detail})
    except Exception as e:
        return make_error(_id, -32000, "Internal MCP error", {"detail": str(e)})
