# Todo: SousChef.ai

## Fase 0 — Scaffold backend
- [x] `backend/` con uv: pyproject.toml (entrypoint app.main:app), .python-version, .env.example, .gitignore
- [x] config.py (pydantic-settings: proveedor LLM, Gemini, DATABASE_URL, static, CORS)
- [x] db.py (engine + init_db + SessionDep), models.py (Ingredient), seed.py (~23 ingredientes)
- [x] main.py: CORS, /static, routers, app.frontend() con SPA fallback

## Fase 1 — CRUD ingredientes
- [x] schemas.py + routers/ingredients.py (GET/POST/PATCH/DELETE, 409, rutas sin trailing slash)
- [x] tests: test_ingredients.py (CRUD + duplicados + 404)

## Fase 2 — Deducción
- [x] Servicio descontar_stock (normalización, faltantes, transacción)
- [x] routers/recipes.py: POST /api/recipes/cook (200 / 409 con detalle)
- [x] tests: test_cook.py

## Fase 3 — Agente IA
- [x] agent/tools.py: get_inventario, descontar_stock, TOOL_DEFS compartidas (OpenAI/Gemini)
- [x] agent/llm.py: proveedores `local` (llama.cpp/OpenAI-compatible) y `gemini` (thought signatures)
- [x] agent/agent.py: orquestación SSE (token/tool_call/tool_result/recipe/recipe_image/done/error)
- [x] agent/image_service.py: imagen con Gemini, cache por hash (null si no hay key)
- [x] routers/chat.py: POST /api/chat → EventSourceResponse
- [x] tests: test_chat.py (proveedores con transportes mockeados, retry de errores transitorios)

## Fase 4 — Scaffold frontend
- [x] Vite + Vue3 + TS + Tailwind v4 + Router + Pinia + vitest + vue-tsc
- [x] main.css, App.vue, AppLayout + NavBar, rutas / y /chat

## Fase 5 — Feature Despensa
- [x] lib/api.ts + stores/pantry.ts
- [x] IngredientForm, IngredientList, IngredientItem, IngredientFilters, PantryView

## Fase 6 — Feature Chat
- [x] lib/sse.ts (POST + ReadableStream) + stores/chat.ts
- [x] ChatInput, ChatMessage, RecipeCard (spinner + botón cocinar), ChatView

## Fase 7 — Integración y proveedores
- [x] app.frontend() sirve dist; README; verificación e2e
- [x] Proveedor local: llama-server + Qwen3.5-4B (scripts/serve_local.sh), config LLM_PROVIDER
- [x] Verificación e2e real: tool calling local, multi-turno (receta + descontar_stock), parser SSE
- [x] Revisión final: 26 tests backend + 11 frontend, ruff, type-check

## Fase 8 — Unidades por envase y gramos
- [x] Ingredient.gramos_por_unidad + migración idempotente (`db.migrate`) + seed (atún: lata 140 g)
- [x] Conversión unit-aware en descontar_stock: mismo envase, mismo gramaje, unidad incompatible
- [x] UI: form, item y card muestran gramos/envase; get_inventario expone gramos_por_unidad al LLM
- [x] Tests: test_cook.py (envases, kg→g, incompatibles, 409 con detalle en gramos)

## Fase 9 — Vista de recetas
- [x] stores/recipes.ts (localStorage `souschef.recipes.v1`, prune 7 días) + watch del chat
- [x] RecipeCard: "Ver receta" (chat), solo clicable (lista), corazón favorito, "Cocinar receta" (detalle)
- [x] RecetasView (Receta del día / Generadas hoy / Favoritas) + RecipeDetailView (/recetas/:hash)
- [x] Toasts + AppModal; tests: recipes store, RecipeCard, RecipesView, RecipeDetailView
- [x] specs/recetas.md

## Fase 10 — Robustez del chat e imágenes
- [x] Markdown del LLM renderizado con marked + DOMPurify (MarkdownText.vue); strong en basil-700
- [x] Sin `<pre>` crudo: el backend no streamea el JSON cercado (recorte en ```); strip/trim/highlight del nombre en chat.ts
- [x] /cook tolerante: normalize_recipe() + payload dict → 400; mensaje amigable ante 422 en la card
- [x] Imagen con fallback web: IMAGE_SOURCE (auto/gemini/web), TheMealDB (tier free) → Wikimedia Commons
- [x] Test: test_image_service.py; 38 tests backend + 50 frontend
