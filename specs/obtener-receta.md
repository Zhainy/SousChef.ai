# Spec: Obtener la receta cuando el chat responde solo con texto

## Objective
A veces el asistente responde con texto pero sin la ficha de receta (sin el bloque JSON
que dispara el evento `recipe`). El usuario debe poder pedir esa receta con un botón:

1. Si el **último** mensaje del asistente tiene texto y **no** trae receta ni error, se
   muestra un botón **"Obtener la receta"**.
2. Al pulsarlo, el backend re-emite un turno con `force_recipe=True`: el LLM convierte su
   respuesta anterior al formato de ficha JSON.
3. La card de receta aparece **dentro del mismo mensaje**, debajo del texto existente
   (sin crear burbujas nuevas). El botón queda en estado "Obteniendo receta…" mientras corre.

## Scope
- Backend: solo el flag `force_recipe` en `ChatRequest` y un hint en el system prompt.
  No cambia el esquema SSE (reusa `recipe`/`recipe_image`/`done`/`error`).
- Frontend: nueva acción `forceRecipe()` en el store de chat + botón en `ChatMessage`.
- No cambia `SavedRecipe` ni `localStorage`; no hay migraciones.

## Tech Stack
- Backend: FastAPI + pydantic (`ChatRequest`), proveedores local/Gemini en `agent/llm.py`.
- Frontend: Vue 3 (`<script setup lang="ts">`), Pinia, Tailwind v4, vitest.

## Data / API
- `POST /api/chat` acepta además `force_recipe: boolean` (default `false`):
  ```json
  { "messages": [...], "force_recipe": true }
  ```
- Eventos SSE sin cambios. Con `force_recipe=True` el hint del system prompt pide
  convertir la respuesta anterior a la ficha JSON.

## Backend
- `schemas.py` — `ChatRequest.force_recipe: bool = False`.
- `llm.py` — constante `FORCE_RECIPE_HINT`:
  > El usuario acaba de pedirte la ficha de una receta. Convierte tu respuesta anterior
  > al formato de ficha: presentación breve de 1-2 frases + bloque ```json (esquema
  > del sistema). Entrega la receta aunque falte algún ingrediente (la más cercana
  > con lo disponible).
  - `local_stream(history, client=None, force_recipe=False)` → lo añade al system message.
  - `gemini_stream(history, client=None, force_recipe=False)` → `_tool_config(force_recipe)`
    lo añade a `system_instruction`.
- `agent.py` — `stream_chat(messages, client=None, force_recipe=False)` lo propaga.
- `routers/chat.py` — pasa `payload.force_recipe`.

## Frontend
### `stores/chat.ts` — `forceRecipe(): Promise<void>`
- Guards: existe último mensaje, `role === 'assistant'`, tiene `content`, **sin** `recipe`
  y **sin** `error`, y no hay `streaming` en curso. Si no, no hace nada.
- `streaming = true`; re-emite la misma historia con `{ messages, force_recipe: true }`
  (no crea un mensaje de usuario inventado).
- Aplica eventos **sobre el último entry** (no crea mensajes):
  - `recipe` → `entry.recipe = data`, `entry.imagePending = true`.
  - `recipe_image` → `entry.imagePending = false`, `entry.imageUrl = image_url`.
  - `error` → `entry.error = message`.
  - `token`/`tool_call`/`tool_result` se ignoran (no se duplica narrativa).
- Si el turno termina sin `recipe` ni `error` → `entry.error = "No pude convertir la
  respuesta en una receta. Inténtalo de nuevo."`
- Errores de red → `entry.error`; siempre `streaming = false` al final.

### `ChatMessage.vue`
- Usa `useChatStore()`.
- `canAskRecipe` = el entry es el **último** de la conversación, asistente, con `content`,
  sin `recipe` y sin `error`.
- Botón **"Obtener la receta"** (`data-test="ask-recipe"`) → `store.forceRecipe()`.
- Mientras `store.streaming` con este entry activo → spinner **"Obteniendo receta…"**
  (`data-test="asking-recipe"`).

## Boundaries
- Backend: `uv run ruff check` + `uv run pytest` antes de cerrar.
- Frontend: `npm run type-check` + `npm run test`.
- No tocar la pipeline SSE ni el shape de `SavedRecipe`.
- `force_recipe` es un hint (no una garantía): si el LLM vuelve a responder sin JSON,
  el frontend muestra un error amigable.

## Testing
- **Backend** (`tests/test_chat.py`):
  - `local_stream` con `force_recipe=True` incluye el hint en el system message capturado
    (transporte MockTransport); sin el flag, no está.
  - `gemini_stream` con `force_recipe=True` inyecta el hint en `config.system_instruction`
    (config capturado por el FakeModels); y produce evento `recipe`.
  - Endpoint `POST /api/chat` acepta `force_recipe: true` (200, SSE).
- **Frontend**:
  - `stores/chat.test.ts` — `forceRecipe` adjunta la card al mensaje existente (misma
    cantidad de mensajes), envía `force_recipe: true`, respeta guards (con receta / usuario /
    sin contenido / mientras streamea no hace nada), maneja error de stream y turno sin receta.
  - `ChatMessage.test.ts` — requiere pinia activo; botón solo en el último mensaje texto-sin-receta;
    oculto si es de usuario, ya tiene receta, tiene error o no es el último; click llama `forceRecipe`;
    estado "Obteniendo receta…".

## Success Criteria
- Respuesta de texto sin receta → aparece "Obtener la receta" en el último mensaje.
- Click → la card (con imagen) aparece en el mismo mensaje, sin burbujas nuevas.
- Si el LLM no entrega JSON, el usuario ve un error claro.
- Backend y frontend en verde (`pytest`, `type-check`, `vitest`).

## Open Questions
- (Resuelto) Card en el mismo mensaje. Botón solo en el último mensaje. Backend con hint
  `force_recipe` (más fiable que un re-prompt solo de frontend).
