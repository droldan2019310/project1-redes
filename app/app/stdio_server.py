# app/stdio_server.py
import sys, json, asyncio, re
from fastapi import HTTPException

from app.mcp_server import (
    PROTOCOL_VERSION, SERVER_NAME, SERVER_VERSION,
    TOOLS, make_result, make_error,
    _call_analyze, _call_transform, _call_send_mock, _call_order_paid
)

# ---- Helpers de framing ----
HEADER_RE = re.compile(rb"^Content-Length:\s*(\d+)\r?\n$", re.IGNORECASE)

async def read_framed_message(reader: asyncio.StreamReader):
    """
    Lee un mensaje con encabezados estilo LSP:
      Content-Length: <N>\r\n
      \r\n
      <N bytes de JSON>
    Devuelve dict del body o None si EOF.
    """
    # Lee encabezados hasta línea vacía
    headers = []
    while True:
        line = await reader.readline()
        if not line:
            return None  # EOF
        if line in (b"\r\n", b"\n"):  # fin de headers
            break
        headers.append(line)

    length = None
    for h in headers:
        m = HEADER_RE.match(h.strip())
        if m:
            length = int(m.group(1))
            break
    if length is None:
        # Sin Content-Length: protocolo inválido
        return {"jsonrpc": "2.0", "id": None, "method": None, "_parse_error": "Missing Content-Length"}

    body = await reader.readexactly(length)
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return {"jsonrpc": "2.0", "id": None, "method": None, "_parse_error": "Invalid JSON body"}

def write_framed_message(obj: dict):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    sys.stdout.write(f"Content-Length: {len(data)}\r\n\r\n")
    sys.stdout.flush()
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()

def write_ndjson(obj: dict):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()

async def handle_jsonrpc(body: dict):
    if body is None or body.get("_parse_error"):
        return make_error(None, -32700, body.get("_parse_error", "Parse error"))

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
            return make_error(_id, -32601, f"Method not found: {name}")

        return make_error(_id, -32601, f"Unknown method: {method}")

    except HTTPException as he:
        return make_error(_id, -32000, "Internal MCP error", {"status": he.status_code, "detail": he.detail})
    except Exception as e:
        # Log a stderr para depurar
        print(f"[stdio_server] Exception: {e}", file=sys.stderr, flush=True)
        return make_error(_id, -32000, "Internal MCP error", {"detail": str(e)})

async def main():
  
    loop = asyncio.get_event_loop()

    # Preparar lector desde stdin (binario)
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin.buffer)

    # Modo detección: lee un “peek” para decidir
    # (Si comienza con 'Content-Length', usamos framing. Si parece JSON, usamos NDJSON.)
    # Leemos una línea; si es header, seguimos con framed; si es JSON, seguimos NDJSON.
    first_line = await reader.readline()
    if not first_line:
        return

    # ¿Framed?
    is_framed = bool(HEADER_RE.match(first_line.strip()))
    if is_framed:
        # Procesa este header y el resto como framed
        pending_header = first_line
        while True:
            headers = [pending_header]
            # consume el resto de headers hasta línea vacía
            while True:
                line = await reader.readline()
                if not line:
                    return
                headers.append(line)
                if line in (b"\r\n", b"\n"):
                    break
            # Busca Content-Length
            length = None
            for h in headers:
                m = HEADER_RE.match(h.strip())
                if m:
                    length = int(m.group(1))
                    break
            if length is None:
                resp = make_error(None, -32600, "Missing Content-Length")
                write_framed_message(resp)
                continue

            body = await reader.readexactly(length)
            try:
                req = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                resp = make_error(None, -32700, "Parse error")
            else:
                # Si es notificación (sin id), procesamos pero no respondemos
                resp = await handle_jsonrpc(req)
                # Solo respondemos si tiene id (JSON-RPC request). Notificaciones -> sin respuesta
                if req.get("id") is None:
                    # Aun así logeamos a stderr
                    print(f"[stdio_server] notif handled: {req.get('method')}", file=sys.stderr, flush=True)
                    pending_header = await reader.readline()
                    if not pending_header:
                        return
                    continue
            write_framed_message(resp)
            pending_header = await reader.readline()
            if not pending_header:
                return

    else:
        # NDJSON: la primera línea debería ser JSON
        try:
            req = json.loads(first_line.decode().strip())
        except json.JSONDecodeError:
            resp = make_error(None, -32700, "Parse error")
            write_ndjson(resp)
        else:
            resp = await handle_jsonrpc(req)
            # Notificación -> no respondas
            if req.get("id") is not None:
                write_ndjson(resp)

        # Sigue leyendo NDJSON
        while True:
            line = await reader.readline()
            if not line:
                break
            s = line.decode().strip()
            if not s:
                continue
            try:
                req = json.loads(s)
            except json.JSONDecodeError:
                resp = make_error(None, -32700, "Parse error")
                write_ndjson(resp)
                continue

            resp = await handle_jsonrpc(req)
            if req.get("id") is not None:
                write_ndjson(resp)

if __name__ == "__main__":
    asyncio.run(main())
