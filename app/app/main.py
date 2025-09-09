
import os, httpx, hashlib


# from .models import OdooInvoice, ZohoSalesOrder  # se usan en los mocks (lo dejamos)
from .models import OdooInvoice, ZohoSalesOrder
from .mcp_server import mcp as mcp_router

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

app.include_router(mcp_router)

