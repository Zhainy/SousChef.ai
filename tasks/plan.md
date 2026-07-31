# Plan: SousChef.ai

## Fases (orden por dependencias)

- **Fase 0 — Scaffold backend**: `backend/` con uv, pyproject (entrypoint `app.main:app`), config (pydantic-settings), `db.py`, `models.py`, `seed.py`, `.env.example`, `main.py` con CORS + `/static` + `app.frontend()` condicional. Verificación: `uv sync` + import de la app.
- **Fase 1 — CRUD ingredientes**: `schemas.py` + `routers/ingredients.py` (GET/POST/PATCH/DELETE, 409 en nombres duplicados) + pytest.
- **Fase 2 — Deducción**: servicio `descontar_stock` (normalización, chequeo previo, transacción, rollback) + `routers/recipes.py` (`POST /api/recipes/cook`, 409 con detalle) + tests.
- **Fase 3 — Agente IA**: `agent/tools.py` (get_inventario, descontar_stock), `agent/agent.py` (bucle tool-calling + streaming SSE + extracción de receta), `agent/image_service.py` (generación con cache por hash), `routers/chat.py` (SSE) + tests con cliente mockeado. Depende de F1/F2.
- **Fase 4 — Scaffold frontend**: Vite + Vue 3 + TS + Tailwind v4 + Router + Pinia + vitest. (Paralelo con F1–F3.)
- **Fase 5 — Feature Despensa**: `lib/api.ts`, `stores/pantry.ts`, componentes pantry (list, form, filters, item), vista + navegación.
- **Fase 6 — Feature Chat**: `lib/sse.ts`, `stores/chat.ts`, componentes chat (input, message, RecipeCard con spinner + botón cocinar), integración con `/api/recipes/cook`.
- **Fase 7 — Integración**: servir `dist` desde backend, README, verificación end-to-end, revisión final.

## Dependencias
```
F0 → F1 → F2 → F3 → F6
F4 → F5 → F6
F3 → F6 (contrato SSE)
```

## Riesgos y mitigaciones
- API key Gemini ausente → `.env.example` + error mapeado a evento `error`; tests con cliente mockeado.
- Nombres de ingrediente divergentes modelo↔BD → inventario pasado como nombres exactos + match normalizado.
- SSE nativo (`EventSource`) no soporta POST → `lib/sse.ts` lee `response.body` de un `fetch` POST.
- Doble deducción (botón + chat) → un único servicio transaccional compartido.
- Latencia de imagen (5–15 s) → texto primero, spinner, evento `recipe_image`, cache por hash.

## Verificación
- Cada fase: `uv run pytest` (backend) / `npm run type-check` (frontend).
- Final: flujo e2e manual (CRUD, chat con clave real, cocinar receta).
