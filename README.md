# MCP Orchestrator – README

Servidor **MCP** mínimo para orquestar pedidos: recibe eventos de “pagado”, valida, transforma a payloads para **Odoo** y **Zoho**, y expone endpoints para análisis con **Ollama**.

---
# Instalación de Ollama Local

## 📦 macOS (Homebrew)

```bash
# 1. Instala Ollama
brew install ollama

# 2. Inicia el servicio
ollama serve

# 3. Descarga el modelo que usarás (ejemplo: llama3.1)
ollama pull llama3.1

# 4. Probar un prompt rápido
ollama run llama3.1 "Hola, ¿qué puedes hacer?"


## 📦 linux

```bash
# 1. Instala Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Inicia el servicio
ollama serve

# 3. Descarga el modelo
ollama pull llama3.1

# 4. Probar un prompt rápido
ollama run llama3.1 "Hola mundo"

## 📦 windows

```bash
# 1. Instala Ollama
instala https://ollama.com/download
# 2. Inicia el servicio
ollama serve

# 3. Descarga el modelo
ollama pull llama3.1

# 4. Probar un prompt rápido
ollama run llama3.1 "Hola mundo"

---
## 1) Requisitos

- **Docker** y **Docker Compose**
- **Ollama** instalado y corriendo localmente  
  - macOS:
    ```bash
    brew install ollama
    ollama serve
    ollama pull llama3.1
    ```
- **curl** o **Postman** para pruebas

> Nota: El contenedor MCP llama a Ollama en tu host (`http://host.docker.internal:11434`). Asegúrate de tener `ollama serve` activo.

---

## 2) Estructura del proyecto (mínima)

```
mcp-server/
├─ docker-compose.yml
├─ .env
├─ init/
│  ├─ 001_orders.sql
│  ├─ 002_order_items.sql
│  └─ 003_integration_logs.sql   # opcional
└─ app/
   ├─ Dockerfile
   ├─ requirements.txt
   └─ app/
      ├─ main.py
      ├─ db.py
      ├─ queries.py
      ├─ redis_kv.py
      ├─ validate.py
      ├─ transform.py
      └─ models.py
```

---

## 3) Variables de entorno (`.env`)

Ejemplo:

```env
# FastAPI
PORT=8080

# MySQL
MYSQL_HOST=mcp_mysql
MYSQL_PORT=3306
MYSQL_DB=mcp_db
MYSQL_USER=mcp
MYSQL_PASSWORD=mcp_pass

# Redis
REDIS_HOST=mcp_redis
REDIS_PORT=6379

# Ollama
OLLAMA_HOST=host.docker.internal
OLLAMA_PORT=11434
OLLAMA_MODEL=llama3.1

# Seguridad webhook
MCP_WEBHOOK_SECRET=changeme

# Reglas negocio
PAID_STATUS_ID=2
ORG_ID_ZOHO=test-org

# Sinks (mocks locales)
SINK_ODOO_URL=http://127.0.0.1:8080/mock/odoo/invoices
SINK_ZOHO_URL=http://127.0.0.1:8080/mock/zoho/salesorders

# Prompt por defecto para /orders/analyze (opcional)
ANALYZE_PROMPT=Eres un asistente MCP de integraciones. Analiza la orden y responde en español, breve y claro...
```

---

## 4) Levantar servicios

```bash
docker compose build --no-cache
docker compose up -d
docker compose logs -f mcp_server
```

> Si es la **primera vez**, MySQL ejecutará automáticamente los `.sql` en `init/` (crea tablas y datos dummy).  
> Si ya existía el volumen y agregaste nuevos `.sql`, o quieres resembrar:  
> `docker compose down -v && docker compose up -d --build`

---

## 5) Endpoints principales

### 5.1 Healthcheck
- **GET** `http://localhost:8080/health`  
Comprueba que el servicio y Ollama están accesibles.

```bash
curl http://localhost:8080/health
```

---

### 5.2 Prompt libre al LLM
- **POST** `http://localhost:8080/llm/complete`

```bash
curl -s http://localhost:8080/llm/complete \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Explica qué hace este MCP en 1 línea."}'
```

---

### 5.3 Analizar una orden con LLM
- **POST** `http://localhost:8080/orders/analyze`

```bash
curl -s http://localhost:8080/orders/analyze \
  -H "Content-Type: application/json" \
  -d '{"order_id":1,"prompt":"¿El subtotal de los items coincide con el total de la orden?"}' | jq
```

---

### 5.4 Transformar orden → payloads (sin enviar)
- **POST** `http://localhost:8080/orders/transform`

```bash
curl -s http://localhost:8080/orders/transform \
  -H "Content-Type: application/json" \
  -d '{"order_id":1}' | jq
```

---

### 5.5 Webhook: order paid
- **POST** `http://localhost:8080/webhooks/order_paid`

```bash
curl -s http://localhost:8080/webhooks/order_paid \
  -H "Content-Type: application/json" \
  -d '{"secret":"changeme","source":"laravel-core","order_id":1}' | jq
```

---

### 5.6 Mocks

#### Odoo
```bash
curl -s http://localhost:8080/mock/odoo/invoices \
  -H "Content-Type: application/json" \
  -d '{ "invoice_ref": "1", "partner": {"name":"Juan Pérez","vat":"CF","email":"juan@example.com","phone":"5555-1234", "address":{"street":"Av. Reforma 123","city":"Guatemala","state":"Guatemala","country":"GT"}}, "currency":"GTQ", "invoice_lines":[{"name":"Item","quantity":1,"price_unit":10.0,"tax_amount":0,"subtotal":10.0}], "total_expected":10.0 }' | jq
```

#### Zoho
```bash
curl -s http://localhost:8080/mock/zoho/salesorders \
  -H "Content-Type: application/json" \
  -d '{ "reference_number":"SO-001","customer_name":"Juan Pérez","line_items":[{"name":"Item","quantity":1,"rate":10.0}] }' | jq
```

---

### 5.7 Enviar automáticamente a los mocks
- **POST** `http://localhost:8080/orders/send_mock`

```bash
curl -s http://localhost:8080/orders/send_mock \
  -H "Content-Type: application/json" \
  -d '{"order_id":1}' | jq
```

---

## 6) Base de datos

- `init/001_orders.sql` → crea `orders` y carga 12 dummy
- `init/002_order_items.sql` → crea `order_items` y carga ítems
- `init/003_integration_logs.sql` → opcional

---


## 8) Roadmap

- Conectar APIs reales Odoo/Zoho
- Logs de integración
- Reintentos automáticos
- Seguridad (API keys / JWT)

---
