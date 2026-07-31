# Spec: SousChef.ai — Despensa + Agente de IA

## Objective
Aplicación web que combina un CRUD de despensa (Vue 3) con un chat de agente de IA (FastAPI + Gemini). El agente valida el inventario real vía Tool Calling, sugiere recetas usando únicamente ingredientes disponibles y descuenta stock de forma atómica al cocinar (botón o pedido por chat).

## Tech Stack
- **Backend**: Python 3.12, FastAPI, SQLModel/SQLite, uv, Ruff, `google-genai` SDK, Pillow, pytest.
- **Frontend**: Vue 3 (`<script setup lang="ts">`), Pinia, Vue Router, Tailwind CSS v4, Vite, vitest.
- **IA**: Google Gemini. Modelo de chat configurable (`GEMINI_MODEL`, default `gemini-3-flash-preview`); modelo de imagen configurable (`IMAGE_MODEL`, default `gemini-3-pro-image-preview`).

## Commands
| Capa | Comando |
|---|---|
| Backend dev | `uv run fastapi dev` |
| Backend test | `uv run pytest` |
| Backend lint | `uv run ruff check` |
| Backend format | `uv run ruff format` |
| Frontend dev | `npm run dev` |
| Frontend build | `npm run build` |
| Frontend typecheck | `npm run type-check` |
| Frontend test | `npm run test` |

## Project Structure
```
backend/
  app/
    main.py            # app FastAPI, CORS, /static, app.frontend() para prod
    config.py          # Settings (pydantic-settings), lee .env
    db.py              # engine, init_db, SessionDep
    models.py          # SQLModel: Ingredient
    schemas.py         # Pydantic: IngredientCreate/Update, Recipe, StockResult, Chat
    seed.py            # ~18 ingredientes iniciales
    routers/
      ingredients.py   # CRUD REST /api/ingredients
      recipes.py       # POST /api/recipes/cook (deducción síncrona)
      chat.py          # POST /api/chat → SSE
    agent/
      tools.py         # get_inventario(), descontar_stock() (y registro)
      agent.py         # bucle tool-calling + streaming, extractor de receta
      image_service.py # genera imagen del plato, cache por hash
  tests/               # pytest + TestClient (cliente Gemini mockeado)
  static/recipes/      # imágenes generadas (gitignored)
  pyproject.toml       # [tool.fastapi] entrypoint = "app.main:app"
  .env.example
frontend/
  src/
    main.ts, App.vue, assets/main.css (Tailwind v4)
    router/index.ts
    stores/pantry.ts, stores/chat.ts
    lib/api.ts, lib/sse.ts
    features/pantry/{PantryView,IngredientForm,IngredientList,IngredientItem,IngredientFilters}.vue
    features/chat/{ChatView,ChatMessage,ChatInput,RecipeCard}.vue
    components/layout/{AppLayout,NavBar}.vue
specs/SPEC.md, tasks/plan.md, tasks/todo.md
.gitignore
```

## Data Model
```
Ingredient: id:int, nombre:str(unique), cantidad:float(>=0), unidad:str,
            categoria:str, created_at:datetime
```
- Unidades: `g, kg, ml, l, piezas, unidades, cucharadas, cucharaditas, pizca, al gusto`.
- Categorías: `proteínas, verduras, frutas, lácteos, granos, especias, otros`.
- Emparejamiento para deducción: nombre normalizado (lowercase + trim).

## API
- `GET /api/ingredients` → `Ingredient[]`
- `POST /api/ingredients` (201) — 409 si el nombre ya existe (insensible a mayúsculas)
- `PATCH /api/ingredients/{id}` — actualización parcial; 409 si choca con otro nombre
- `DELETE /api/ingredients/{id}` (204)
- `POST /api/recipes/cook` `{nombre, ingredientes:[{nombre,cantidad}], ...}` → descuenta en transacción; **409** con detalle por ingrediente si falta stock
- `POST /api/chat` `{messages:[{role,content}]}` → `EventSourceResponse`
  - Eventos SSE:
    - `token` `{delta}` — texto parcial del modelo
    - `tool_call` `{name, args}` — la IA invoca una herramienta (spinner en UI)
    - `tool_result` `{name, result}`
    - `recipe` `{nombre, resumen, tiempo_minutos, ingredientes, instrucciones, hash, image_url:null}`
    - `recipe_image` `{hash, image_url}` — imagen generada (o `null` si falló → placeholder)
    - `done` `{message}` — fin del turno
    - `error` `{message}` — error no recuperable

## Agent Design
- Tools: `get_inventario()` y `descontar_stock(ingredientes:[{nombre,cantidad}])`. Ambas usan el mismo servicio de dominio que `/api/recipes/cook` → comportamiento consistente y atómico.
- System prompt en español: exige usar nombres exactos del inventario y unidades coherentes; las recetas se devuelven con un bloque JSON cercado (```json) que el backend extrae para la card.
- Estrategia de streaming: `generate_content_stream` por turno. Los `FunctionCall` llegan completos al final del turno (sin `stream_function_call_arguments`); el texto se reenvía como `token`. Tras ejecutar tools se continúa el bucle; sin tool calls → se emite `recipe`/`done`.
- Imagen: `generate_recipe_image` genera con Gemini (`response_modalities=["IMAGE"]`), guarda en `static/recipes/{hash}.png`, cachea por hash de la receta. Emitida como evento `recipe_image`. Fallo → `image_url: null`.

## Testing Strategy
- **Backend (pytest + TestClient)**: CRUD completo, `/cook` (éxito, stock insuficiente 409, ingrediente inexistente, rollback), tools del agente, chat con cliente Gemini mockeado (bucle de tools, streaming, extracción de receta).
- **Frontend (vitest + @vue/test-utils)**: `IngredientForm`, `RecipeCard`, `useChatStore` con stream simulado.
- Cobertura objetivo: rutas CRUD, servicio de deducción, extracción de receta.

## Boundaries
- **Always**: `ruff check` + `pytest` antes de cerrar backend; `type-check` en frontend; API key solo en `.env` (nunca en git); validación Pydantic de inputs.
- **Ask first**: cambios de esquema de BD, añadir dependencias, cambiar proveedor de IA.
- **Never**: commitear `.env`/claves; commitear `*.db`; romper tests sin aprobación.

## Success Criteria
- CRUD funcional desde la UI y desde Swagger (`/docs`).
- El chat streamea tokens, consulta inventario real y sugiere recetas solo con ingredientes disponibles.
- "Cocinar receta" (botón) y pedido por chat reducen la despensa atómicamente; stock insuficiente → 409 con detalle mostrado en la UI.
- Las cards de receta muestran imagen generada por IA con spinner mientras se genera.

## Open Questions
- (Resuelto) Proveedor de IA: **Gemini**. Streaming: **SSE**. Recetas: **JSON estructurado**. Semilla: **sí**. Imagen: **IA con spinner**.
