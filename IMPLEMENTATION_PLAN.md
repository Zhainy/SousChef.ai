# SousChef.ai — Plan de Implementación: OCI + Docker + IA Híbrida

> **Versión:** 1.0  
> **Fecha:** Septiembre 2026  
> **Stack actual:** FastAPI · SQLModel/SQLite · Vue 3 · Tailwind v4 · llama.cpp / Qwen3.5  
> **Objetivo:** Migrar a una arquitectura containerizada con Docker Compose, desplegable en OCI Always Free (ARM A1), con IA híbrida (OCI Generative AI primario + llama.cpp fallback) e HTTPS via Let's Encrypt.

---

## Tabla de Contenidos

1. [Decisiones de Diseño](#1-decisiones-de-diseño)
2. [Arquitectura Propuesta](#2-arquitectura-propuesta)
3. [Estructura de Archivos Final](#3-estructura-de-archivos-final)
4. [Diseño de la Capa de IA Híbrida](#4-diseño-de-la-capa-de-ia-híbrida)
5. [Estrategia de Imágenes (sin Gemini)](#5-estrategia-de-imágenes-sin-gemini)
6. [Variables de Entorno](#6-variables-de-entorno)
7. [Task Breakdown](#7-task-breakdown)
8. [Hoja de Ruta](#8-hoja-de-ruta)
9. [Recursos OCI Always Free](#9-recursos-oci-always-free)

---

## 1. Decisiones de Diseño

### Frontend serving

**Nginx como reverse proxy.** Un contenedor Nginx sirve el `dist/` de Vue y hace proxy de `/api/`
al backend FastAPI. Separación de responsabilidades, assets estáticos con gzip/caché, y HTTPS
centralizado en un solo punto.

### Docker Compose: base + override

**`docker-compose.yml` base** para desarrollo local + **`docker-compose.prod.yml`** para OCI.
La práctica estándar de la industria: un solo comando en cada entorno, sin duplicar configuración.

```bash
# Desarrollo local
docker compose up

# Producción OCI
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Modelo GGUF en OCI

**Bind mount sobre el Block Volume de 200 GB (Always Free).** El archivo `.gguf` (~2.5 GB) vive
en `/opt/souschef/models/` dentro de la instancia OCI. La imagen Docker de `llama.cpp` es ligera;
el modelo se sube una sola vez vía `scp`. Sin costo adicional, dentro del cupo gratuito permanente.

### Terraform vs. Manual

**Terraform** para provisionar la infraestructura OCI. Para un portafolio técnico, el IaC en el
repo demuestra madurez de ingeniería y hace la infraestructura reproducible y auditable.

| | Manual (OCI Console) | Terraform |
|---|---|---|
| Reproducibilidad | ❌ Pasos no versionados | ✅ `terraform apply` desde cero |
| Portafolio | ❌ Invisible en el repo | ✅ El IaC está en el repo |
| Errores humanos | ❌ Un paso mal rompe todo | ✅ Declarativo, idempotente |
| Documentación viva | ❌ README largo con capturas | ✅ El código ES la documentación |
| Tiempo setup inicial | ✅ 30 min | ⚠️ 1–2 horas la primera vez |

Terraform crea: VCN, subnet pública, Internet Gateway, Security List (puertos 22/80/443),
instancia A1 con Ubuntu 22.04 ARM64, Dynamic Group + Policy para Instance Principal.

### Eliminación de Gemini

La integración con Gemini (text LLM e image generation) se **elimina completamente** del proyecto:

- `gemini_stream()` en `llm.py` → reemplazado por `oci_stream()`
- `_gemini_bytes()` en `image_service.py` → eliminado, reemplazado por pipeline web gratuita
- Dependencia `google-genai` en `pyproject.toml` → eliminada
- Campos `gemini_api_key`, `gemini_model`, `image_model` en `config.py` → eliminados

**Motivación:** Cuota gratuita de Gemini insuficiente para uso normal, imágenes generadas
inconsistentes, y la arquitectura OCI cubre todos los casos de uso con mejor resiliencia.

---

## 2. Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────────────┐
│                OCI Always Free — ARM A1 (2 OCPU / 12 GB RAM)        │
│                                                                       │
│  ┌─────────────────── Terraform ──────────────────────┐              │
│  │  VCN 10.0.0.0/16                                   │              │
│  │   └── Subnet Pública 10.0.0.0/24                   │              │
│  │        ├── Internet Gateway                         │              │
│  │        ├── Security List (:22 :80 :443)             │              │
│  │        └── Instancia A1 (Ubuntu 22.04 ARM64)        │              │
│  └────────────────────────────────────────────────────┘              │
│                                                                       │
│  ┌─────────────────── Docker Compose ─────────────────┐              │
│  │                                                     │              │
│  │   nginx:alpine                                      │              │
│  │   :80  → redirect HTTPS                            │              │
│  │   :443 → SPA + proxy /api → backend:8000           │              │
│  │                                                     │              │
│  │   souschef-backend (FastAPI :8000)                  │              │
│  │   souschef-llama   (llama-server :8080)             │              │
│  │   certbot          (Let's Encrypt, renovación auto) │              │
│  └────────────────────────────────────────────────────┘              │
│                                                                       │
│  ┌─────── Block Volume 200 GB (Always Free) ──────────┐              │
│  │  /opt/souschef/                                     │              │
│  │    data/souschef.db   ← SQLite                      │              │
│  │    models/*.gguf      ← modelo llama.cpp            │              │
│  │    certbot/           ← certificados SSL            │              │
│  └────────────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                │
                │ HTTPS :443
                ▼
           [Internet / Usuario]

┌──────────────────────────────┐
│  OCI Services (us-ashburn-1) │
│  OCI Generative AI           │
│  meta.llama-3.3-70b-instruct │
│  (primario, on-demand)       │
└──────────────────────────────┘
```

---

## 3. Estructura de Archivos Final

```
souschef-ai/
├── IMPLEMENTATION_PLAN.md          ← este archivo
│
├── terraform/                      # NUEVO — Infraestructura OCI
│   ├── main.tf                     # VCN, subnet, instancia A1, IAM
│   ├── variables.tf                # tenancy_ocid, region, ssh_key, shape
│   ├── outputs.tf                  # IP pública, comandos post-deploy
│   ├── terraform.tfvars.example   # plantilla sin secretos
│   └── .gitignore                  # excluye .tfvars, .tfstate, .terraform/
│
├── docker-compose.yml              # NUEVO — base (desarrollo local)
├── docker-compose.prod.yml         # NUEVO — override OCI producción
├── .env.example                    # MODIFICADO — sin Gemini, con OCI
│
├── nginx/                          # NUEVO
│   ├── nginx.conf                  # reverse proxy + HTTPS + SPA routing
│   └── Dockerfile                  # FROM nginx:alpine
│
├── backend/
│   ├── Dockerfile                  # NUEVO — multi-stage, ARM64-compatible
│   ├── .dockerignore               # NUEVO
│   └── app/
│       ├── config.py               # MODIFICADO — +OCI vars, -Gemini vars
│       └── agent/
│           ├── llm.py              # MODIFICADO — +oci_stream(), -gemini_stream()
│           ├── agent.py            # MODIFICADO — +fallback logic, +provider_info SSE
│           └── image_service.py    # MODIFICADO — -Gemini, +Unsplash, pipeline limpia
│
├── llama-cpp/                      # NUEVO
│   └── Dockerfile                  # ghcr.io/ggerganov/llama.cpp:server (multi-arch)
│
├── frontend/
│   ├── Dockerfile                  # NUEVO — multi-stage build
│   └── src/
│       └── stores/
│           └── chat.ts             # MODIFICADO — manejo evento provider_info
│
└── scripts/
    ├── serve_local.sh              # existente
    └── deploy_oci.sh               # NUEVO — setup post-Terraform en instancia OCI
```

---

## 4. Diseño de la Capa de IA Híbrida

### Flujo de decisión en `stream_chat()`

```
POST /api/chat
      │
      ▼
LLM_PROVIDER == "oci" ?
      │
    ┌─┴──── Sí ────┐
    │               │
    ▼               ▼
oci_stream()    local_stream()
    │
  ¿Error ANTES de emitir tokens?
  (timeout / 429 / red / sin credenciales)
    │
    └── AI_FALLBACK_ENABLED == true ?
            │
           Sí → local_stream()  ←──────────────────────────────┐
            │                                                    │
            └── emite SSE: provider_info {provider: "local",    │
                                          fallback: true}        │
                                                                 │
  Sin error → emite SSE: provider_info {provider: "oci",        │
                                        fallback: false} ────────┘
```

### Secuencia completa de eventos SSE

```
provider_info   → {"provider": "oci"|"local", "fallback": bool}
token           → {"delta": "..."}              (0..N veces)
tool_call       → {"name": "...", "args": {...}} (si hay herramientas)
tool_result     → {"name": "...", "result": "..."} 
recipe          → {"nombre": "...", "hash": "...", "image_url": null, ...}
recipe_image    → {"hash": "...", "image_url": "/static/recipes/xyz.png" | null}
done            → {"message": "texto final visible"}
```

### Autenticación OCI por entorno

| Entorno | `OCI_AUTH_TYPE` | Mecanismo |
|---|---|---|
| Desarrollo local | `api_key` | Lee `~/.oci/config` montado como volumen read-only |
| Producción OCI | `instance_principal` | IAM role de la VM, sin archivos ni secrets en el contenedor |

### Clase `AIProviderError`

```python
class AIProviderError(Exception):
    """Error recuperable de un proveedor de IA. Activa el fallback si procede."""
    def __init__(self, provider: str, cause: Exception):
        self.provider = provider
        self.cause = cause
        super().__init__(f"[{provider}] {cause}")
```

El fallback solo se activa si **no se ha emitido ningún token todavía** — evita streams incompletos
que confundirían al usuario.

---

## 5. Estrategia de Imágenes (sin Gemini)

### Pipeline gratuita, sin API keys

```
generate_recipe_image(recipe, hash)
         │
         ├─ 1. Cache en disco ────────────────────────── hit → retorna URL local
         │      /static/recipes/{hash}.png
         │
         ├─ 2. TheMealDB API ─────────────────────────── hit → descarga, guarda, retorna URL local
         │      (búsqueda por nombre + traducción términos comunes)
         │      (gratuita, sin auth, ~60k recetas)
         │
         ├─ 3. Unsplash Source ───────────────────────── siempre tiene resultado
         │      https://source.unsplash.com/800x450/?{nombre} food recipe
         │      (redirect 302 a foto real, sin API key, sin límite de cuota)
         │      → retorna URL externa directamente (no se descarga)
         │
         └─ 4. None → frontend muestra placeholder SVG (ya implementado)
```

### Mejoras concretas vs. implementación anterior

| Problema anterior | Solución nueva |
|---|---|
| Gemini Image API: cuota mínima, imágenes inconsistentes | Eliminado completamente |
| Wikimedia Commons: búsqueda imprecisa, resultados no relacionados | Reemplazado por Unsplash Source |
| TheMealDB no encuentra recetas en español | Diccionario de traducción de términos comunes (arroz→rice, pollo→chicken, etc.) |
| Sin imagen = error silencioso | Unsplash garantiza imagen de comida relevante como último recurso |

---

## 6. Variables de Entorno

### `.env.example` completo

```ini
# ── Proveedor de IA ─────────────────────────────────────────────────────────
# Valores: oci | local
LLM_PROVIDER=oci
AI_FALLBACK_ENABLED=true
AI_FALLBACK_PROVIDER=local

# ── OCI Generative AI (primario) ─────────────────────────────────────────────
# Obtener en: OCI Console → Identity → Compartments (OCID del compartment)
OCI_COMPARTMENT_ID=ocid1.compartment.oc1..xxxxxx
OCI_REGION=us-ashburn-1
OCI_MODEL_ID=meta.llama-3.3-70b-instruct
OCI_SERVICE_ENDPOINT=https://inference.generativeai.us-ashburn-1.oci.oraclecloud.com
# local: api_key (lee ~/.oci/config) | OCI server: instance_principal
OCI_AUTH_TYPE=api_key
OCI_TIMEOUT_SECONDS=30

# ── llama.cpp (fallback) ──────────────────────────────────────────────────────
# En Docker Compose, el nombre del servicio es "llama-cpp"
LOCAL_LLM_BASE_URL=http://llama-cpp:8080/v1
LOCAL_LLM_MODEL=qwen3.5-4b

# ── Imágenes de recetas ───────────────────────────────────────────────────────
# Valores: web | none (none desactiva la búsqueda, útil para tests)
IMAGE_SOURCE=web

# ── Base de datos ─────────────────────────────────────────────────────────────
DATABASE_URL=sqlite:////data/souschef.db

# ── CORS ──────────────────────────────────────────────────────────────────────
ALLOW_ORIGINS=http://localhost,https://tudominio.com
```

### Campos eliminados respecto a la versión anterior

```ini
# ELIMINADOS — ya no se usan
# GEMINI_API_KEY=
# GEMINI_MODEL=gemini-3.5-flash
# IMAGE_MODEL=gemini-3-pro-image-preview
```

---

## 7. Task Breakdown

### [x] Task 1 — Preparar la capa de configuración

**Objetivo:** Extender `config.py` y `.env.example` para soportar OCI sin romper la configuración
actual. Eliminar los campos de Gemini.

**Archivos modificados:** `backend/app/config.py`, `.env.example`

**Cambios en `config.py`:**
- Eliminar: `gemini_api_key`, `gemini_model`, `image_model`
- Simplificar: `image_source: str = "web"` (valores: `web` | `none`)
- Agregar:
  ```python
  oci_compartment_id: str | None = None
  oci_region: str = "us-ashburn-1"
  oci_model_id: str = "meta.llama-3.3-70b-instruct"
  oci_service_endpoint: str | None = None
  oci_auth_type: str = "api_key"        # api_key | instance_principal
  oci_timeout_seconds: int = 30
  ai_fallback_enabled: bool = True
  ai_fallback_provider: str = "local"
  ```
- Actualizar default: `local_llm_base_url: str = "http://llama-cpp:8080/v1"`

**Tests:** Test unitario que valida que `Settings` carga con y sin vars OCI y que los defaults
son correctos. Test que confirma que campos Gemini ya no existen en `Settings`.

**Demo:** `python -c "from app.config import settings; print(settings.model_dump())"` muestra
los campos OCI con sus defaults sin errores, sin campos Gemini.

---

### [x] Task 2 — Implementar `oci_stream()` como nuevo proveedor LLM

**Objetivo:** Crear `oci_stream()` en `agent/llm.py` que respeta el contrato de `TurnEvent`
existente, usando la API compatible con OpenAI de OCI Generative AI.

**Archivos modificados:** `backend/app/agent/llm.py`, `backend/pyproject.toml`

**Implementación:**
- Instalar `oci` en `pyproject.toml` (versión exacta, no open range).
- OCI Generative AI Responses API es compatible con OpenAI — `oci_stream()` reutiliza la lógica
  de `local_stream()` con estos cambios:
  - URL base: `{OCI_SERVICE_ENDPOINT}/20231130/actions/chat`
  - Autenticación: OCI request signing via `oci.auth.signers`
  - Para `api_key`: usa `oci.config.from_file()` + `oci.signer.Signer`
  - Para `instance_principal`: usa `oci.auth.signers.InstancePrincipalsSecurityTokenSigner`
  - Implementar `OCIRequestSigner` adaptado a `httpx` que inyecta headers `Authorization` y `x-date`
- Reutilizar `TRANSIENT_CODES`, `_is_transient()`, `MAX_ATTEMPTS`, `RETRY_DELAY` ya existentes.
- Emite los mismos `TurnEvent` que `local_stream`: `token`, `tool_call`, `tool_result`, `text`.
- Lanza `AIProviderError` en fallos no-transientes o tras agotar reintentos.

**Tests:** Test con `httpx.MockTransport` que simula una respuesta SSE de OCI y verifica que
`oci_stream()` emite los `TurnEvent` en el orden correcto.

**Demo:** Con `LLM_PROVIDER=oci` y credenciales reales, `POST /api/chat` responde con
sugerencias de recetas generadas por `meta.llama-3.3-70b-instruct`.

---

### [x] Task 3 — Implementar el patrón fallback en `stream_chat()`

**Objetivo:** Fallback transparente OCI → llama.cpp ante cualquier fallo que ocurra antes de
emitir tokens al cliente.

**Archivos modificados:** `backend/app/agent/agent.py`, `backend/app/agent/llm.py`

**Implementación:**
- Definir `class AIProviderError(Exception)` en `llm.py`.
- En `stream_chat()`, agregar `elif settings.llm_provider == "oci"` al switch de proveedor.
- Eliminar la rama `if client is not None or settings.llm_provider == "gemini"` junto con
  la validación de `gemini_api_key`.
- Envolver `async for event in events` en `try/except AIProviderError`:
  - Si falla OCI antes de emitir tokens y `settings.ai_fallback_enabled` es `True`,
    reiniciar con `local_stream()` y marcar `fallback=True`.
  - Si ya se emitieron tokens, propagar el error normalmente.
- Emitir evento SSE `provider_info` al inicio del stream:
  ```python
  yield ServerSentEvent(
      data={"provider": "oci", "fallback": False},
      event="provider_info",
  )
  ```

**Tests:** Test que inyecta `oci_stream` que lanza `asyncio.TimeoutError` y verifica que:
1. La respuesta completa llega desde `local_stream()`.
2. El evento `provider_info` contiene `{"provider": "local", "fallback": true}`.

**Demo:** Con `LLM_PROVIDER=oci` y credenciales inválidas, el chat responde usando llama.cpp.
El evento `provider_info` visible en las DevTools indica el origen del fallback.

---

### [x] Task 3b — Refactorizar `image_service.py` — eliminar Gemini, mejorar pipeline web

**Objetivo:** Limpiar toda dependencia de Gemini del servicio de imágenes y reemplazar la
búsqueda imprecisa por una pipeline gratuita, confiable y sin API keys.

**Archivos modificados:** `backend/app/agent/image_service.py`, `backend/pyproject.toml`

**Implementación:**
- Eliminar: `_gemini_bytes()`, imports de `google.genai`, `from PIL import Image` (verificar si
  `_crop_16_9` era la única razón para Pillow — si es así, eliminar también `Pillow`).
- Eliminar: `MEALDB_SEARCH_URL` no — mantenerlo, mejorarlo.
- **Mejorar `_meal_db_thumb()`:**
  - Agregar diccionario de traducción de términos comunes ES→EN:
    ```python
    TRANSLATION_MAP = {
        "pollo": "chicken", "arroz": "rice", "pasta": "pasta",
        "carne": "beef", "cerdo": "pork", "pescado": "fish",
        "tomate": "tomato", "queso": "cheese", "huevo": "egg",
        # ... etc.
    }
    ```
  - Intentar búsqueda con nombre original + nombre con términos traducidos.
- **Agregar `_unsplash_thumb()`:**
  - Sin descarga, sin API key. Retorna URL directa que el browser resuelve via redirect 302.
  - URL: `https://source.unsplash.com/800x450/?{keywords}` donde `keywords` es el nombre
    de la receta URL-encoded + ` food recipe`.
- **Pipeline final en `generate_recipe_image`:**
  1. Cache en disco → retorna URL local
  2. `_meal_db_thumb()` → descarga, guarda en disco, retorna URL local
  3. `_unsplash_thumb()` → retorna URL externa directamente (sin guardar en disco)
  4. `None` → el frontend muestra el placeholder SVG existente
- Actualizar `image_source` en `config.py`: `"web"` (activo) o `"none"` (para tests).
- Eliminar `google-genai` de `pyproject.toml`.

**Tests:**
- Test que mockea `httpx.get` para TheMealDB y verifica que retorna la URL correcta.
- Test que verifica que con `image_source="none"` retorna `None` sin llamadas de red.
- Test que verifica el cache hit (no llama a ninguna API).
- Test que verifica que la traducción de términos mejora los resultados de TheMealDB.

**Demo:** Una receta de "Arroz con Pollo" genera una imagen relevante. La misma receta en
segunda consulta retorna inmediatamente desde cache sin llamadas de red.

---

### [x] Task 4 — Dockerfile del backend (multi-stage, ARM64-compatible)

**Objetivo:** Imagen Docker optimizada para ARM64 (OCI A1) y AMD64 (desarrollo local x86).

**Archivos creados:** `backend/Dockerfile`, `backend/.dockerignore`

**Implementación:**
```dockerfile
# Stage 1: builder
FROM python:3.12-slim AS builder
RUN pip install uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# Stage 2: runtime
FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app/ ./app/
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`.dockerignore`:
```
.venv/
__pycache__/
*.pyc
tests/
*.db
.env
.pytest_cache/
.ruff_cache/
```

La base de datos se espera en `/data/souschef.db` via `DATABASE_URL=sqlite:////data/souschef.db`
montado como volumen — nunca dentro de la imagen.

**Tests:** `docker build --platform linux/arm64 -t souschef-backend backend/` sin errores.
`docker run --rm souschef-backend python -c "from app.config import settings; print('OK')"`.

**Demo:** Imagen buildea en < 2 min, arranca Uvicorn, responde `GET /api/ingredients` con `[]`.

---

### [x] Task 5 — Dockerfile de llama.cpp para ARM64

**Objetivo:** Contenedor `llama-server` multi-arch con el modelo GGUF montado como volumen.

**Archivos creados:** `llama-cpp/Dockerfile`

**Implementación:**
```dockerfile
FROM ghcr.io/ggml-org/llama.cpp:server

ENV MODEL_PATH=/models/Qwen3.5-4B-Q4_K_M.gguf
ENV LLAMA_PORT=8080
ENV LLAMA_CTX=8192
ENV LLAMA_THREADS=4
ENV LLAMA_ARG_REASONING=on
ENV LLAMA_ARG_THINK_BUDGET=1024

EXPOSE 8080

ENTRYPOINT ["/bin/sh", "-c", \
  "/app/llama-server -m ${MODEL_PATH} --port ${LLAMA_PORT} \
   --ctx-size ${LLAMA_CTX} --threads ${LLAMA_THREADS} \
   --host 0.0.0.0 \"$@\"", "--"]
```

La imagen oficial `ghcr.io/ggml-org/llama.cpp:server` soporta ARM64 y AMD64 nativamente.
El modelo GGUF **no se incluye en la imagen** — se monta desde el host.

**Tests:** `docker run -v /path/to/model:/models souschef-llama` arranca y responde en `/health`.

**Demo:** `curl http://localhost:8080/v1/models` devuelve el modelo disponible.

---

### [x] Task 6 — Dockerfile del frontend + Nginx con HTTPS

**Objetivo:** Frontend Vue servido por Nginx con HTTPS (Let's Encrypt) y redirect HTTP→HTTPS.

**Archivos creados:** `frontend/Dockerfile`, `nginx/nginx.conf`, `nginx/Dockerfile`

**`frontend/Dockerfile`:**
```dockerfile
# Stage 1: build
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: serve
FROM nginx:alpine AS serve
COPY --from=build /app/dist /usr/share/nginx/html
COPY ../nginx/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80 443
```

**`nginx/nginx.conf`** — dos bloques `server`:

```nginx
# HTTP → HTTPS redirect
server {
    listen 80;
    server_name _;
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl;
    server_name tudominio.com;

    ssl_certificate     /etc/letsencrypt/live/tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tudominio.com/privkey.pem;

    # SPA routing
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        gzip_static on;
    }

    # Proxy al backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    location /static/ {
        proxy_pass http://backend:8000;
    }

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header Referrer-Policy no-referrer-when-downgrade;
}
```

**Certbot** se ejecuta como servicio Docker separado con renovación automática cada 12 horas.

**Tests:** `docker build -t souschef-frontend frontend/` sin errores. SPA carga en `localhost:80`.

**Demo:** En OCI con dominio real, `https://tudominio.com` sirve la app con certificado válido.
HTTP redirige a HTTPS con código 301.

---

### [x] Task 7 — `docker-compose.yml` base (desarrollo local)

**Objetivo:** Stack completo para desarrollo local con un solo `docker compose up`.

**Archivos creados:** `docker-compose.yml`

```yaml
services:
  backend:
    build: ./backend
    volumes:
      - ./backend/app:/app/app       # hot-reload en dev
      - ./data:/data                  # persistencia SQLite
    env_file: .env
    command: >
      uvicorn app.main:app
      --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"                   # expuesto en dev para debugging
    depends_on:
      - llama-cpp

  llama-cpp:
    build: ./llama-cpp
    volumes:
      - ${MODELS_DIR:-./models}:/models
    environment:
      MODEL_PATH: /models/${LLAMA_MODEL_FILE:-Qwen3.5-4B-Q4_K_M.gguf}
    ports:
      - "8080:8080"

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
```

Agregar a `.gitignore`:
```
data/
models/
```

**Tests:** `docker compose up --build && curl localhost/api/ingredients` retorna `[]`.

**Demo:** `docker compose up` desde cero levanta la app completa en < 5 min. UI funciona,
chat responde (llama.cpp local o OCI según `.env`).

---

### [x] Task 8 — `docker-compose.prod.yml` override para OCI

**Objetivo:** Override de producción para OCI: sin hot-reload, volúmenes en Block Volume,
HTTPS activo, restart policies, certbot integrado.

**Archivos creados:** `docker-compose.prod.yml`

```yaml
services:
  backend:
    restart: unless-stopped
    volumes:
      - /opt/souschef/data:/data       # Block Volume OCI
    command: >
      uvicorn app.main:app
      --host 0.0.0.0 --port 8000 --workers 2
    ports: []                           # sin puerto expuesto al exterior

  llama-cpp:
    restart: unless-stopped
    volumes:
      - /opt/souschef/models:/models
    deploy:
      resources:
        limits:
          memory: 8G
    ports: []

  frontend:
    restart: unless-stopped
    volumes:
      - /opt/souschef/certbot/conf:/etc/letsencrypt
      - /opt/souschef/certbot/www:/var/www/certbot
    ports:
      - "80:80"
      - "443:443"

  certbot:
    image: certbot/certbot
    restart: unless-stopped
    volumes:
      - /opt/souschef/certbot/conf:/etc/letsencrypt
      - /opt/souschef/certbot/www:/var/www/certbot
    entrypoint: >
      /bin/sh -c "trap exit TERM;
      while :; do certbot renew --webroot
      -w /var/www/certbot --quiet; sleep 12h; done"
```

**Comando de producción:**
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Tests:** `docker compose -f docker-compose.yml -f docker-compose.prod.yml config`
— merge correcto, puertos internos no expuestos.

---

### [x] Task 9 — Infraestructura OCI con Terraform

**Objetivo:** Provisionar toda la infraestructura OCI necesaria dentro del Always Free,
versionada en el repo, reproducible con un solo comando.

**Archivos creados:** `terraform/main.tf`, `terraform/variables.tf`,
`terraform/outputs.tf`, `terraform/terraform.tfvars.example`, `terraform/.gitignore`

**`terraform/variables.tf`:**
```hcl
variable "tenancy_ocid" {
  description = "OCID del tenancy raíz de OCI"
}
variable "user_ocid" {
  description = "OCID del usuario de OCI para Terraform"
}
variable "fingerprint" {
  description = "Fingerprint de la API key del usuario"
}
variable "private_key_path" {
  description = "Path al archivo PEM de la API key privada"
}
variable "region" {
  default     = "us-ashburn-1"
}
variable "ssh_public_key" {
  description = "Clave SSH pública para acceso a la instancia"
}
variable "instance_shape_ocpus" {
  default = 2
  description = "OCPUs para la instancia A1 (max 4 en Always Free)"
}
variable "instance_shape_memory_gb" {
  default = 12
  description = "RAM en GB para la instancia A1 (max 24 en Always Free)"
}
```

**`terraform/main.tf`** crea los siguientes recursos:

| Recurso Terraform | Tipo OCI | Descripción |
|---|---|---|
| `oci_core_vcn` | Virtual Cloud Network | `10.0.0.0/16` |
| `oci_core_internet_gateway` | Internet Gateway | Acceso a internet para la subnet |
| `oci_core_route_table` | Route Table | Ruta default `0.0.0.0/0` → IGW |
| `oci_core_security_list` | Security List | Ingress TCP 22/80/443; egress `0.0.0.0/0` |
| `oci_core_subnet` | Subnet Pública | `10.0.0.0/24` |
| `oci_core_instance` | VM.Standard.A1.Flex | Ubuntu 22.04 ARM64, `user_data` instala Docker |
| `oci_identity_dynamic_group` | Dynamic Group | Incluye la instancia A1 |
| `oci_identity_policy` | IAM Policy | Permite uso de OCI Generative AI sin API keys |

**`user_data` cloud-init en la instancia:**
```bash
#!/bin/bash
apt-get update -y
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
usermod -aG docker opc
mkdir -p /opt/souschef/{data,models,certbot}
cd /opt/souschef
git clone https://github.com/tu-usuario/souschef-ai.git app
```

**IAM Policy:**
```hcl
resource "oci_identity_policy" "souschef_genai" {
  name           = "souschef-genai-policy"
  description    = "Permite a la instancia SousChef usar OCI Generative AI"
  compartment_id = var.tenancy_ocid
  statements = [
    "Allow dynamic-group souschef-instances to use generative-ai-family in tenancy"
  ]
}
```

**`terraform/outputs.tf`:**
```hcl
output "instance_public_ip" {
  value = oci_core_instance.souschef.public_ip
}
output "next_steps" {
  value = <<-EOT
    1. Subir el modelo GGUF:
       scp Qwen3.5-4B-Q4_K_M.gguf opc@${oci_core_instance.souschef.public_ip}:/opt/souschef/models/
    2. Conectar a la instancia:
       ssh opc@${oci_core_instance.souschef.public_ip}
    3. Configurar el .env y arrancar el stack (ver scripts/deploy_oci.sh)
  EOT
}
```

**`terraform/.gitignore`:**
```
terraform.tfvars
*.tfstate
*.tfstate.backup
.terraform/
.terraform.lock.hcl
```

**Tests:** `terraform validate` y `terraform plan` sin errores.
`terraform apply` crea todos los recursos en < 3 min.

**Demo:** `terraform output` muestra la IP pública. `ssh opc@<ip>` conecta a la instancia.
Docker está instalado y el repo clonado en `/opt/souschef/app`.

---

### Task 10 — Script `deploy_oci.sh` + documentación en README.md

**Objetivo:** Automatizar los pasos post-Terraform y documentar el flujo completo de despliegue
en el README para que sea reproducible por cualquier persona desde el repo.

**Archivos creados/modificados:** `scripts/deploy_oci.sh`, `README.md`

**`scripts/deploy_oci.sh`:**
```bash
#!/bin/bash
# deploy_oci.sh — Ejecutar en la instancia OCI después de terraform apply
set -e

SOUSCHEF_DIR="/opt/souschef"
APP_DIR="${SOUSCHEF_DIR}/app"

echo "→ Creando directorios..."
mkdir -p "${SOUSCHEF_DIR}/{data,models,certbot/conf,certbot/www}"

echo "→ Configurando .env..."
if [ ! -f "${APP_DIR}/.env" ]; then
    cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
    echo ""
    echo "⚠️  ACCIÓN REQUERIDA: editar ${APP_DIR}/.env con:"
    echo "   - OCI_COMPARTMENT_ID"
    echo "   - OCI_AUTH_TYPE=instance_principal"
    echo "   - ALLOW_ORIGINS=https://tudominio.com"
    echo ""
fi

echo "→ Verificando que el modelo GGUF existe..."
if [ -z "$(ls -A ${SOUSCHEF_DIR}/models/*.gguf 2>/dev/null)" ]; then
    echo "⚠️  No se encontró archivo .gguf en ${SOUSCHEF_DIR}/models/"
    echo "   Subir el modelo antes de continuar:"
    echo "   scp Qwen3.5-4B-Q4_K_M.gguf opc@<IP>:${SOUSCHEF_DIR}/models/"
    exit 1
fi

echo "→ Emitiendo certificado SSL inicial (Let's Encrypt)..."
echo "   Asegurate de que el DNS del dominio apunte a esta IP antes de continuar."
read -p "   Dominio (ej: souschef.tudominio.com): " DOMAIN
docker run --rm \
    -v "${SOUSCHEF_DIR}/certbot/conf:/etc/letsencrypt" \
    -v "${SOUSCHEF_DIR}/certbot/www:/var/www/certbot" \
    -p 80:80 \
    certbot/certbot certonly --standalone \
    -d "${DOMAIN}" --non-interactive --agree-tos -m admin@${DOMAIN}

echo "→ Arrancando el stack de producción..."
cd "${APP_DIR}"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo ""
echo "✓ SousChef.ai desplegado en https://${DOMAIN}"
```

**Sección "Deploy to OCI" en `README.md`:**

```markdown
## Deploy to OCI (Always Free)

### Pre-requisitos
- Cuenta OCI activa (us-ashburn-1)
- Terraform >= 1.5 instalado localmente
- `~/.oci/config` configurado con API key de tu usuario OCI
- Dominio apuntando a la IP pública de la instancia (paso 4)

### Pasos

1. **Clonar el repo y configurar Terraform:**
   cp terraform/terraform.tfvars.example terraform/terraform.tfvars
   # Editar terraform.tfvars con tus OCIDs y SSH key

2. **Provisionar la infraestructura:**
   cd terraform && terraform init && terraform apply

3. **Subir el modelo GGUF a la instancia:**
   scp Qwen3.5-4B-Q4_K_M.gguf opc@$(terraform output -raw instance_public_ip):/opt/souschef/models/

4. **Apuntar el DNS del dominio a la IP pública:**
   terraform output instance_public_ip
   # Crear registro A en tu proveedor de DNS

5. **Conectar a la instancia y desplegar:**
   ssh opc@$(terraform output -raw instance_public_ip)
   bash /opt/souschef/app/scripts/deploy_oci.sh

6. **La app estará disponible en https://tudominio.com**
```

---

### Task 11 — Configuración Instance Principal + badge proveedor en frontend + validación E2E

**Objetivo:** Conectar el stack completo a OCI Generative AI con Instance Principal (sin
secrets en el servidor), agregar indicador visual del proveedor activo en la UI, y validar
los tres escenarios de funcionamiento.

**Archivos modificados:** `frontend/src/stores/chat.ts`, componente de chat en Vue

**Instance Principal en OCI:**
- El Dynamic Group y la Policy creados en Task 9 habilitan la instancia para usar OCI
  Generative AI sin archivos de configuración ni API keys.
- En el `.env` del servidor: `OCI_AUTH_TYPE=instance_principal`
- Para desarrollo local: `OCI_AUTH_TYPE=api_key` + volumen `~/.oci/config` montado read-only:
  ```yaml
  # en docker-compose.yml (solo para dev)
  backend:
    volumes:
      - ~/.oci:/root/.oci:ro
  ```

**Badge de proveedor en el frontend:**
- El evento SSE `provider_info` actualiza un Pinia store (`aiProviderStore`).
- Un badge pequeño en la esquina del chat muestra el proveedor activo:
  - `✦ OCI AI` — azul — cuando responde OCI Generative AI
  - `⚡ Local AI` — gris — cuando responde llama.cpp
  - `⚡ Local AI (fallback)` — amarillo — cuando hubo fallback automático
- El badge no afecta el flujo del chat, es informativo.

**Validación de los 3 escenarios:**

| Escenario | Configuración | Resultado esperado |
|---|---|---|
| OCI primario funciona | `LLM_PROVIDER=oci`, credenciales válidas | Respuesta de `meta.llama-3.3-70b-instruct`, badge `OCI AI` |
| Fallback por timeout | `OCI_TIMEOUT_SECONDS=1`, servidor lento | Respuesta de llama.cpp, badge `Local AI (fallback)` |
| Fallback por sin credenciales | `OCI_AUTH_TYPE=api_key`, sin `~/.oci/config` | Respuesta de llama.cpp, badge `Local AI (fallback)` |

**Tests:** Test de integración E2E con `httpx.AsyncClient` que envía un mensaje y verifica
que llega `event: done` con texto coherente para ambos proveedores.

**Demo:** App desplegada en OCI responde con `meta.llama-3.3-70b-instruct`. Al deshabilitar
la Policy IAM, la siguiente respuesta viene de llama.cpp automáticamente, sin intervención
del usuario, con el badge actualizándose en tiempo real.

---

## 8. Hoja de Ruta

```
SEMANA 1 — Capa de IA y Limpieza
──────────────────────────────────────────────────────────
 Task 1  │ Config OCI vars, eliminar Gemini config       │ 1 día
 Task 2  │ oci_stream() — nuevo proveedor LLM            │ 2 días
 Task 3  │ Fallback logic en stream_chat()               │ 1 día
 Task 3b │ Refactorizar image_service.py sin Gemini      │ 1 día

SEMANA 2 — Containerización
──────────────────────────────────────────────────────────
 Task 4  │ Dockerfile backend (multi-stage, ARM64)       │ 1 día
 Task 5  │ Dockerfile llama-cpp                          │ 0.5 día  ┐ paralelo
 Task 6  │ Dockerfile frontend + Nginx + HTTPS           │ 1.5 días ┘
 Task 7  │ docker-compose.yml base                       │ 0.5 día
 Task 8  │ docker-compose.prod.yml override OCI          │ 0.5 día

SEMANA 3 — Infraestructura y Despliegue
──────────────────────────────────────────────────────────
 Task 9  │ Terraform — VCN, A1, IAM, Dynamic Group       │ 2 días
 Task 10 │ Script deploy_oci.sh + README                 │ 1 día
 Task 11 │ Instance Principal + badge UI + E2E           │ 2 días

Dependencias:
  Task 2 requiere Task 1
  Task 3 requiere Task 2
  Tasks 4/5/6 pueden hacerse en paralelo con Tasks 2/3
  Task 7 requiere Tasks 4/5/6
  Task 8 requiere Task 7
  Task 9 puede hacerse en paralelo con Task 8
  Task 10 requiere Task 9
  Task 11 requiere Tasks 3, 8, 9
```

---

## 9. Recursos OCI Always Free

### Cuota utilizada vs. disponible

| Recurso | Usado | Cuota Always Free |
|---|---|---|
| Instancia A1 (OCPUs) | 2 | 4 total gratuitos |
| Instancia A1 (RAM) | 12 GB | 24 GB total gratuitos |
| Block Volume | ~10 GB (OS + Docker + DB + modelo) | 200 GB gratuitos |
| Bandwidth saliente | < 10 GB/mes (estimado) | 10 GB/mes gratuitos |
| OCI Generative AI | On-demand (pay-per-use) | $300 créditos de prueba |
| VCN + Subnet + IGW | 1 cada uno | 2 VCN gratuitas |

### Costo tras agotar créditos de prueba

| Escenario | Costo |
|---|---|
| Solo infra (VM + red + storage) | **$0/mes** — Always Free permanente |
| OCI Generative AI on-demand | ~$0.002/1K tokens input, ~$0.006/1K tokens output |
| Con fallback a llama.cpp | **$0/mes** — modelo local en la propia VM |

El fallback a llama.cpp garantiza **costo cero permanente** incluso después de los créditos.

### Recomendación de shape

Se usan **2 OCPU y 12 GB RAM** (conservador) en lugar del máximo (4 OCPU / 24 GB) para:
1. Dejar margen por si Oracle cambia los límites Always Free en el futuro.
2. Permitir agregar una segunda instancia en el futuro (el cupo total es 4 OCPU / 24 GB
   compartidos entre todas las instancias A1 del tenancy).

El modelo `Qwen3.5-4B-Q4_K_M.gguf` (~2.5 GB) consume ~3 GB de RAM en runtime, cómodo
dentro de los 12 GB asignados.

---

*Plan elaborado como arquitectura de referencia para SousChef.ai — portafolio técnico.*  
*Todos los recursos de infraestructura están dentro de la capa Always Free de OCI.*
