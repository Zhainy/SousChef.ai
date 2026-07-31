# Spec: SousChef.ai — Despensa + Agente de IA

## Objective
Aplicación web que combina un CRUD de despensa (Vue 3) con un chat de agente de IA (FastAPI + Gemini). El agente valida el inventario real vía Tool Calling, sugiere recetas usando únicamente ingredientes disponibles y descuenta stock de forma atómica al cocinar (botón o pedido por chat).

## Tech Stack
- **Backend**: Python 3.12, FastAPI, SQLModel/SQLite, uv, Ruff, `google-genai` SDK, Pillow, httpx, pytest.
- **Frontend**: Vue 3 (`<script setup lang="ts">`), Pinia, Vue Router, Tailwind CSS v4, `marked` + `dompurify`, Vite, vitest.
- **IA**: Google Gemini. Modelo de chat configurable (`GEMINI_MODEL`, default `gemini-3.5-flash`); modelo de imagen configurable (`IMAGE_MODEL`, default `gemini-3-pro-image-preview`). Fuente de imagen configurable (`IMAGE_SOURCE`: `auto`/`gemini`/`web`).

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
    db.py              # engine, migrate() idempotente, init_db, SessionDep
    models.py          # SQLModel: Ingredient (con gramos_por_unidad)
    schemas.py         # Pydantic: CRUD, Recipe, StockResult, Chat + normalize_recipe()
    seed.py            # ~23 ingredientes iniciales (incluye envases con gramos_por_unidad)
    routers/
      ingredients.py   # CRUD REST /api/ingredients
      recipes.py       # POST /api/recipes/cook (normaliza payload, 400/409/200)
      chat.py          # POST /api/chat → SSE
    agent/
      tools.py         # get_inventario(), descontar_stock() (y registro)
      agent.py         # bucle tool-calling + streaming, extractor y normalizador de receta
      image_service.py # imagen (IA o web), cache por hash; null → placeholder
  tests/               # pytest + TestClient (cliente Gemini mockeado)
  static/recipes/      # imágenes generadas/descargadas (gitignored)
  pyproject.toml       # [tool.fastapi] entrypoint = "app.main:app"
  .env.example
frontend/
  src/
    main.ts, App.vue, assets/main.css (Tailwind v4)
    router/index.ts
    stores/pantry.ts, stores/chat.ts, stores/recipes.ts (localStorage)
    lib/api.ts, lib/sse.ts
    components/{AppModal,ToastStack,MarkdownText}.vue, components/ui/
    features/pantry/{PantryView,IngredientForm,IngredientList,IngredientItem,IngredientFilters,SkeletonPantry}.vue
    features/chat/{ChatView,ChatMessage,ChatInput,RecipeCard,TypingIndicator}.vue
    features/recipes/{RecipesView,RecipeDetailView}.vue
    components/layout/{AppLayout,NavBar}.vue
specs/SPEC.md, specs/recetas.md, tasks/plan.md, tasks/todo.md
.gitignore
```

## Data Model
```
Ingredient: id:int, nombre:str(unique), cantidad:float(>=0), unidad:str,
            categoria:str, gramos_por_unidad:float|null(>=0), created_at:datetime
```
- Unidades: `g, kg, ml, l, piezas, unidades, cucharadas, cucharaditas, pizca, al gusto`
  y envases: `lata(s), sobre(s), bolsa(s), paquete(s)`.
- `gramos_por_unidad`: peso de un envase/porción (p. ej. lata de atún = 140 g). Permite
  pedir cantidades en gramos de un ingrediente que se almacena por envases; al cocinar
  se descuentan envases completos y se reporta el detalle en gramos si falta stock.
- Categorías: `proteínas, verduras, frutas, lácteos, granos, especias, otros`.
- Emparejamiento para deducción: nombre normalizado (lowercase + trim).

## API
- `GET /api/ingredients` → `Ingredient[]`
- `POST /api/ingredients` (201) — 409 si el nombre ya existe (insensible a mayúsculas)
- `PATCH /api/ingredients/{id}` — actualización parcial; 409 si choca con otro nombre
- `DELETE /api/ingredients/{id}` (204)
- `POST /api/recipes/cook` `{nombre, ingredientes:[{nombre,cantidad,unidad?}], ...}` — acepta
  un dict crudo, lo normaliza con `normalize_recipe()` (400 si no quedan ingredientes
  válidos) y descuenta en transacción; **409** con detalle por ingrediente si falta stock
- `POST /api/chat` `{messages:[{role,content}]}` → `EventSourceResponse`
  - Eventos SSE:
    - `token` `{delta}` — texto parcial del modelo
    - `tool_call` `{name, args}` — la IA invoca una herramienta (spinner en UI)
    - `tool_result` `{name, result}`
    - `recipe` `{nombre, resumen, tiempo_minutos, ingredientes, instrucciones, hash, image_url:null}`
    - `recipe_image` `{hash, image_url}` — imagen de la card (IA o web), `null` si falló → placeholder
    - `done` `{message}` — fin del turno
    - `error` `{message}` — error no recuperable

## Agent Design
- Tools: `get_inventario()` y `descontar_stock(ingredientes:[{nombre,cantidad}])`. Ambas usan el mismo servicio de dominio que `/api/recipes/cook` → comportamiento consistente y atómico.
- System prompt en español: exige usar nombres exactos del inventario y unidades coherentes; las recetas se devuelven con un bloque JSON cercado (```json) que el backend extrae para la card. El prompt pide que el texto sea solo una presentación breve (1-2 frases) sin repetir ingredientes/instrucciones.
- Robustez de la salida del LLM: `_extract_recipe` extrae el JSON de la cerca y lo pasa por `normalize_recipe()` (descarta nombres vacíos, `cantidad <= 0`, `tiempo_minutos` inválidos y recorta longitudes). La cerca ``` no se streamea como texto: los tokens se recortan en el primer ``` (`_visible_limit`), así la UI nunca muestra un `<pre>` crudo.
- Estrategia de streaming: `generate_content_stream` por turno. Los `FunctionCall` llegan completos al final del turno (sin `stream_function_call_arguments`); el texto se reenvía como `token`. Tras ejecutar tools se continúa el bucle; sin tool calls → se emite `recipe`/`done`.
- Imagen: `generate_recipe_image` (según `IMAGE_SOURCE`):
  1. `auto` (default): intenta Gemini (`response_modalities=["IMAGE"]`) y, si no hay key o falla, descarga una foto real de la web — **TheMealDB** (`/api/json/v1/1/search.php`, tier free) y luego **Wikimedia Commons** (`"<plato> comida"`, 2 consultas espaciadas 1s para no chocar con el rate limit).
  2. `gemini`: solo IA. `web`: solo web (sin key).
  - La imagen se guarda en `static/recipes/{hash}.png` (cache por hash de la receta) y se emite como `recipe_image`. Si nada funciona → `image_url: null` → la card muestra el placeholder.
  - La descarga a `upload.wikimedia.org` envía `User-Agent` (sin él responde 403).

## Testing Strategy
- **Backend (pytest + TestClient)**: CRUD completo, `/cook` (éxito, stock insuficiente 409, ingrediente inexistente, rollback, unidades por envase y gramos, normalización de payload), tools del agente, chat con cliente Gemini mockeado (bucle de tools, streaming, extracción de receta, recorte de la cerca), `image_service` (caché, fallback web mockeado, placeholder).
- **Frontend (vitest + @vue/test-utils)**: `IngredientForm`, `RecipeCard`, `useChatStore` con stream simulado, `stores/recipes`, `RecipesView`, `RecipeDetailView`, `MarkdownText`.
- Cobertura objetivo: rutas CRUD, servicio de deducción, extracción de receta.

## Boundaries
- **Always**: `ruff check` + `pytest` antes de cerrar backend; `type-check` en frontend; API key solo en `.env` (nunca en git); validación Pydantic de inputs.
- **Ask first**: cambios de esquema de BD, añadir dependencias, cambiar proveedor de IA.
- **Never**: commitear `.env`/claves; commitear `*.db`; romper tests sin aprobación.

## Success Criteria
- CRUD funcional desde la UI y desde Swagger (`/docs`).
- El chat streamea tokens, consulta inventario real y sugiere recetas solo con ingredientes disponibles.
- "Cocinar receta" (botón) y pedido por chat reducen la despensa atómicamente; stock insuficiente → 409 con detalle mostrado en la UI.
- Las cards de receta muestran imagen (IA o descargada de la web) con spinner mientras se obtiene; si no se encuentra ninguna, muestran el placeholder.
- El nombre del plato aparece resaltado en negritas `basil-700` en la respuesta del chat.

## Open Questions
- (Resuelto) Proveedor de IA: **Gemini** (+ local). Streaming: **SSE**. Recetas: **JSON estructurado**. Semilla: **sí**. Imagen: **IA con spinner + fallback web**.
