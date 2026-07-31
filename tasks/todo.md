# Todo: SousChef.ai

## Fase 0 — Scaffold backend
- [ ] `backend/` con uv: pyproject.toml (entrypoint app.main:app), .python-version, .env.example, .gitignore
- [ ] config.py (pydantic-settings: GEMINI_API_KEY, GEMINI_MODEL, IMAGE_MODEL, DATABASE_URL, static, CORS)
- [ ] db.py (engine + init_db + SessionDep), models.py (Ingredient), seed.py (~18 ingredientes)
- [ ] main.py: CORS, /static, routers, app.frontend() condicional
- [ ] Verificar: `uv run python -c "import app.main"`

## Fase 1 — CRUD ingredientes
- [ ] schemas.py (IngredientCreate/Update) + routers/ingredients.py (GET/POST/PATCH/DELETE, 409)
- [ ] tests: test_ingredients.py (CRUD + duplicados + 404)
- [ ] Verificar: `uv run pytest`

## Fase 2 — Deducción
- [ ] Servicio descontar_stock (normalización, faltantes, transacción) en inventario service
- [ ] routers/recipes.py: POST /api/recipes/cook (200 / 409 con detalle)
- [ ] tests: test_cook.py (éxito, insuficiente, inexistente, sin cambios en fallo)
- [ ] Verificar: `uv run pytest`

## Fase 3 — Agente IA
- [ ] agent/tools.py: get_inventario, descontar_stock + registro
- [ ] agent/agent.py: bucle generate_content_stream + tools + extracción de receta + eventos SSE
- [ ] agent/image_service.py: generar imagen (Pillow), cache por hash
- [ ] routers/chat.py: POST /api/chat → EventSourceResponse
- [ ] tests: test_chat.py con cliente mockeado (tools, tokens, recipe, image)
- [ ] Verificar: `uv run pytest`

## Fase 4 — Scaffold frontend
- [ ] Vite + Vue3 + TS + Tailwind v4 + Router + Pinia + vitest + vue-tsc
- [ ] main.css (Tailwind v4), App.vue, AppLayout + NavBar, rutas / y /chat
- [ ] Verificar: `npm run type-check`

## Fase 5 — Feature Despensa
- [ ] lib/api.ts + stores/pantry.ts
- [ ] IngredientForm, IngredientList, IngredientItem, IngredientFilters, PantryView
- [ ] Verificar: `npm run type-check`

## Fase 6 — Feature Chat
- [ ] lib/sse.ts (POST + ReadableStream) + stores/chat.ts
- [ ] ChatInput, ChatMessage, RecipeCard (spinner + botón cocinar), ChatView
- [ ] Verificar: `npm run type-check` + `npm run test`

## Fase 7 — Integración
- [ ] app.frontend() sirve dist; README; verificación e2e
- [ ] Revisión final ruff + pytest + type-check
