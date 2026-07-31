# SousChef.ai — Frontend

Frontend Vue 3 + TypeScript del asistente de cocina. CRUD de despensa, chat con IA
(streaming SSE), cards de receta con imagen y vista de recetas generadas.

## Stack

- Vue 3 (`<script setup lang="ts">`), Pinia, Vue Router, Tailwind CSS v4, Vite, vitest
- `marked` + `dompurify` para renderizar el markdown del asistente de forma segura

## Scripts

| Comando | Descripción |
|---|---|
| `npm run dev` | Dev server en :5173 (proxy a `/api` y `/static`) |
| `npm run build` | `vue-tsc -b && vite build` → `dist/` |
| `npm run type-check` | `vue-tsc -b` |
| `npm run test` | `vitest run` |
| `npm run preview` | Previsualiza el build |

## Estructura

```
src/
  main.ts, App.vue, assets/main.css (Tailwind v4)
  router/index.ts              # /, /chat, /recetas, /recetas/:hash
  stores/
    pantry.ts                  # CRUD de ingredientes
    chat.ts                    # streaming SSE del chat (recibe token/recipe/recipe_image)
    recipes.ts                 # recetas guardadas en localStorage (souschef.recipes.v1)
  lib/
    api.ts                     # cliente fetch + ApiError
    sse.ts                     # SSE vía POST + ReadableStream
  components/
    MarkdownText.vue           # markdown sanitizado (marked + DOMPurify)
    AppModal.vue, ToastStack.vue, ui/
  features/
    pantry/                    # IngredientForm, IngredientList, IngredientItem, IngredientFilters, PantryView, SkeletonPantry
    chat/                      # ChatView, ChatMessage, ChatInput, RecipeCard, TypingIndicator
    recipes/                   # RecipesView (día / generadas hoy / favoritas), RecipeDetailView
  features/layout/             # AppLayout, NavBar
```

## Notas

- El store de recetas persiste en `localStorage` y descarta no favoritas de más de 7 días.
- El nombre del plato se resalta en negritas `basil-700` en la respuesta del chat.
- Tests en `*.test.ts` junto a cada módulo (vitest + @vue/test-utils + jsdom).
