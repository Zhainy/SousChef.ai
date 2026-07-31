# SousChef.ai

Despensa inteligente + asistente de cocina con IA. CRUD de ingredientes en Vue 3 y un
agente que valida el inventario en tiempo real mediante Tool Calling, sugiere recetas
con lo que hay disponible y descuenta el stock al cocinar.

El chat puede usar un **LLM local (llama.cpp)** o **Google Gemini** como proveedor
(`LLM_PROVIDER`). La imagen de cada receta se genera con Gemini o, si eso falla, se
descarga de la web (TheMealDB → Wikimedia Commons) según `IMAGE_SOURCE`; si no se
encuentra ninguna, la card muestra un placeholder.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLModel/SQLite, `google-genai`, Pillow, httpx, uv, Ruff, pytest
- **Frontend**: Vue 3 (Composition API, TypeScript), Pinia, Vue Router, Tailwind CSS v4, `marked` + `dompurify`, Vite, vitest
- **LLM local**: [llama.cpp](https://github.com/ggml-org/llama.cpp) (`llama-server`) con un GGUF de Qwen3.5

## Requisitos

- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 20+
- Para el proveedor local: `llama-server` y un modelo GGUF (p. ej. `Qwen3.5-4B-Q4_K_M.gguf`)
- Para el proveedor Gemini: una API key de Google Gemini (las imágenes también pueden
  usar el fallback web sin key)

## Configuración

```bash
# Backend
cd backend
cp .env.example .env
uv sync

# Frontend
cd ../frontend
npm install
```

Variables del backend (`.env`):

| Variable | Default | Descripción |
|---|---|---|
| `LLM_PROVIDER` | `local` | `local` (llama.cpp) o `gemini` |
| `LOCAL_LLM_BASE_URL` | `http://127.0.0.1:8080/v1` | Endpoint OpenAI-compatible de `llama-server` |
| `LOCAL_LLM_MODEL` | `qwen3.5-4b` | Nombre de modelo enviado a `llama-server` |
| `GEMINI_API_KEY` | — | Clave de Gemini (proveedor `gemini` y generación de imágenes) |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Modelo de chat cuando `LLM_PROVIDER=gemini` |
| `IMAGE_MODEL` | `gemini-3-pro-image-preview` | Modelo de generación de imágenes |
| `IMAGE_SOURCE` | `auto` | `auto` (Gemini y si falla la web), `gemini`, `web` |
| `DATABASE_URL` | `sqlite:///souschef.db` | Conexión a la base de datos |

> **Cuota free tier de Gemini**: la clave gratuita tiene un límite de ~20 requests/día de
> `generate_content` por modelo. Si el chat no responde y aparece un error
> `429 RESOURCE_EXHAUSTED`, es que se agotó la cuota diaria (se renueva cada 24h).
> Los errores transitorios (429/500/502/503) se reintentan automáticamente. Con el
> proveedor local esta cuota no aplica.

## Uso (desarrollo)

```bash
# Terminal 0 — LLM local (solo si LLM_PROVIDER=local)
scripts/serve_local.sh            # llama-server en :8080 con Qwen3.5-4B

# Terminal 1 — backend en :8000 (Swagger en /docs)
cd backend
uv run fastapi dev

# Terminal 2 — frontend en :5173 (proxy a /api y /static)
cd frontend
npm run dev
```

Abre http://localhost:5173

> Las imágenes de receta usan `IMAGE_SOURCE`:
>
> - `auto` (default): intenta generar con Gemini y, si no hay key o falla, busca una
>   foto real del plato en la web (primero **TheMealDB** por nombre y luego
>   **Wikimedia Commons** con la consulta `"<plato> comida"`), la descarga y la cachea.
> - `gemini`: solo generación con IA.
> - `web`: solo búsqueda web (sin key).
>
> Si no se encuentra ninguna imagen, la card muestra un placeholder. La búsqueda web
> usa el tier gratuito de TheMealDB (`/api/json/v1/1/`) y la API pública de Commons.

## Uso (producción)

```bash
cd frontend && npm run build    # genera dist/
cd ../backend
uv run fastapi run             # sirve la app + API en :8000
```

Abre http://localhost:8000

## Comandos

| Capa | Comando |
|---|---|
| Backend dev | `uv run fastapi dev` |
| Backend tests | `uv run pytest` |
| Backend lint/format | `uv run ruff check` / `uv run ruff format` |
| Frontend dev | `npm run dev` |
| Frontend build | `npm run build` |
| Frontend type-check | `npm run type-check` |
| Frontend tests | `npm run test` |

## Arquitectura

```
backend/app/
  main.py            FastAPI app (CORS, /static, frontend)
  config.py          Settings vía pydantic-settings (.env)
  db.py              engine SQLite + SessionDep + migrate() idempotente
  models.py          SQLModel: Ingredient (con gramos_por_unidad)
  schemas.py         Pydantic (CRUD, recetas, chat) + normalize_recipe()
  inventory.py       descontar_stock() — servicio transaccional compartido
  seed.py            datos iniciales de la despensa
  routers/           ingredients (CRUD), recipes (cook), chat (SSE)
  agent/             llm.py (proveedores local/Gemini), tools, imagen con fallback web
frontend/src/
  stores/            pantry (CRUD), chat (streaming SSE), recipes (localStorage)
  lib/               api.ts, sse.ts (SSE vía POST + ReadableStream)
  components/        MarkdownText (markdown sanitizado), AppModal, ToastStack
  features/pantry/   CRUD de la despensa
  features/chat/     chat con cards de receta (imagen + botón cocinar)
  features/recipes/  /recetas (día, generadas hoy, favoritas) y detalle
```

### Cómo funciona el agente

1. El usuario pregunta en el chat. `POST /api/chat` abre un stream SSE.
2. El LLM (local `llama.cpp` o Gemini) llama `get_inventario()` para leer el stock real (Tool Calling).
3. El agente sugiere recetas **solo** con ingredientes disponibles, y devuelve un
   JSON estructurado que el backend extrae y envía como evento `recipe`. La salida se
   normaliza con `normalize_recipe()` (descarta campos inválidos del LLM, p. ej.
   `tiempo_minutos: 0` o ingredientes sin nombre) y el JSON dentro de la cerca ``` no
   se streamea como texto.
4. La card muestra la receta con imagen (IA o descargada de la web; spinner mientras
   se genera, cacheada por hash en `backend/static/recipes/`).
5. "Cocinar receta" llama `POST /api/recipes/cook`; el stock se descuenta en una
   transacción atómica (409 con detalle si falta algún ingrediente).
6. El agente también puede descontar stock por chat con `descontar_stock()`.

### Eventos SSE del chat

| Evento | Payload | Uso |
|---|---|---|
| `token` | `{delta}` | Texto parcial del modelo |
| `tool_call` / `tool_result` | `{name, args}` / `{name, result}` | Indicador de tool en la UI |
| `recipe` | receta + `hash` + `image_url:null` | Card de receta |
| `recipe_image` | `{hash, image_url}` | Imagen de la card (IA o web), o `null` → placeholder |
| `done` | `{message}` | Fin del turno |
| `error` | `{message}` | Error del proveedor o falta de API key |

## Tests

- Backend: `cd backend && uv run pytest` (CRUD, deducción con 409, conversión de unidades
  por envase, proveedores local/Gemini con transportes mockeados, fallback web de imágenes).
- Frontend: `cd frontend && npm run test` (form, recipe card, stores del chat y de recetas,
  vistas de recetas con stream simulado).

## Documentación

- `specs/SPEC.md` — especificación del proyecto
- `specs/recetas.md` — spec de la vista de recetas
- `tasks/plan.md` — plan de implementación
- `tasks/todo.md` — checklist por fases
