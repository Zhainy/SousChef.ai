# SousChef.ai

Despensa inteligente + asistente de cocina con IA. CRUD de ingredientes en Vue 3 y un
agente (FastAPI + Google Gemini) que valida el inventario en tiempo real mediante
Tool Calling, sugiere recetas con lo que hay disponible y descuenta el stock al cocinar.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLModel/SQLite, `google-genai`, Pillow, uv, Ruff, pytest
- **Frontend**: Vue 3 (Composition API, TypeScript), Pinia, Vue Router, Tailwind CSS v4, Vite, vitest

## Requisitos

- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 20+
- Una API key de Google Gemini (para el chat y la generación de imágenes)

## Configuración

```bash
# Backend
cd backend
cp .env.example .env          # pega tu GEMINI_API_KEY aquí
uv sync

# Frontend
cd ../frontend
npm install
```

Variables del backend (`.env`):

| Variable | Default | Descripción |
|---|---|---|
| `GEMINI_API_KEY` | — | Clave de la API de Gemini |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Modelo de chat con Tool Calling |
| `IMAGE_MODEL` | `gemini-3-pro-image-preview` | Modelo de generación de imágenes |
| `DATABASE_URL` | `sqlite:///souschef.db` | Conexión a la base de datos |

> **Cuota free tier**: la clave gratuita tiene un límite de ~20 requests/día de
> `generate_content` por modelo. Si el chat no responde y aparece un error
> `429 RESOURCE_EXHAUSTED`, es que se agotó la cuota diaria (se renueva cada 24h).
> Los errores transitorios (429/500/502/503) se reintentan automáticamente.

## Uso (desarrollo)

```bash
# Terminal 1 — backend en :8000 (Swagger en /docs)
cd backend
uv run fastapi dev

# Terminal 2 — frontend en :5173 (proxy a /api y /static)
cd frontend
npm run dev
```

Abre http://localhost:5173

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
  db.py              engine SQLite + SessionDep
  models.py          SQLModel: Ingredient
  schemas.py         Pydantic (CRUD, recetas, chat)
  inventory.py       descontar_stock() — servicio transaccional compartido
  seed.py            datos iniciales de la despensa
  routers/           ingredients (CRUD), recipes (cook), chat (SSE)
  agent/             tools, bucle tool-calling + streaming, imágenes
frontend/src/
  stores/            pantry (CRUD) y chat (streaming SSE)
  lib/               api.ts, sse.ts (SSE vía POST + ReadableStream)
  features/pantry/   CRUD de la despensa
  features/chat/     chat con cards de receta (imagen + botón cocinar)
```

### Cómo funciona el agente

1. El usuario pregunta en el chat. `POST /api/chat` abre un stream SSE.
2. Gemini llama `get_inventario()` para leer el stock real (Tool Calling).
3. El agente sugiere recetas **solo** con ingredientes disponibles, y devuelve un
   JSON estructurado que el backend extrae y envía como evento `recipe`.
4. La card muestra la receta con imagen generada por IA (spinner mientras se genera,
   cacheada por hash en `backend/static/recipes/`).
5. "Cocinar receta" llama `POST /api/recipes/cook`; el stock se descuenta en una
   transacción atómica (409 con detalle si falta algún ingrediente).
6. El agente también puede descontar stock por chat con `descontar_stock()`.

### Eventos SSE del chat

| Evento | Payload | Uso |
|---|---|---|
| `token` | `{delta}` | Texto parcial del modelo |
| `tool_call` / `tool_result` | `{name, args}` / `{name, result}` | Indicador de tool en la UI |
| `recipe` | receta + `hash` + `image_url:null` | Card de receta |
| `recipe_image` | `{hash, image_url}` | Imagen generada (o `null`) |
| `done` | `{message}` | Fin del turno |
| `error` | `{message}` | Error (ej: falta API key) |

## Tests

- Backend: `cd backend && uv run pytest` (CRUD, deducción con 409, agente con cliente mockeado).
- Frontend: `cd frontend && npm run test` (form, recipe card, store del chat con stream simulado).

## Documentación

- `specs/SPEC.md` — especificación del proyecto
- `tasks/plan.md` — plan de implementación
- `tasks/todo.md` — checklist por fases
