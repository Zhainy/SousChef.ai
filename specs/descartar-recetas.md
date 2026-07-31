# Spec: Descartar recetas — botón de eliminar en la card

## Objective
Que el usuario pueda eliminar una receta que no le guste directamente desde la card de receta, en cualquiera de sus contextos:
1. En el **chat**: la card desaparece del mensaje (se conserva el texto del asistente).
2. En la **lista `/recetas`**: la receta se quita de Receta del día / Generadas hoy / Favoritas.
3. En el **detalle `/recetas/:hash`**: se elimina y la vista vuelve atrás.

Eliminación instantánea + toast **"Deshacer"** para revertir el borrado. Borra todo, incluso favoritas.

## Scope
- **Frontend únicamente**: sin cambios de backend, de BD ni de shape de `SavedRecipe`.
- La key de `localStorage` se mantiene `souschef.recipes.v1` (no hay migración).

## Tech Stack
- Vue 3 (`<script setup lang="ts">`), Pinia, Vue Router, Tailwind v4, vitest. Persistencia manual en `localStorage`.

## Store (`src/stores/recipes.ts`)
Acciones nuevas:
- `remove(hash: string): SavedRecipe | undefined` — elimina la entrada, `persist()` y **devuelve la entrada borrada** para poder restaurarla.
- `restore(entry: SavedRecipe)` — re-inserta la entrada completa preservando `favorited`, `cookedAt` y `createdAt` (no es un upsert por `save()`: ese crearía una entrada nueva con `favorited:false`).

## Toasts (`src/stores/toasts.ts` + `src/components/ToastStack.vue`)
- `Toast` gana `action?: { label: string; onClick: () => void }`.
- `ToastStack` renderiza el botón de acción junto al texto; al clickearlo ejecuta `onClick` y cierra el toast (además del botón "×" existente).
- `notify(message, type, duration)` sin cambios de firma; la acción se pasa por el objeto `Toast` (p. ej. `{ label, onClick }`).

## Componentes
### `RecipeCard.vue` (modificar)
- Botón de **papelera** junto al corazón (`data-test="discard"`, `@click.stop`), mismo patrón visual del corazón: `text-ink-400 hover:text-tomato-600 hover:bg-tomato-50` (neutro en reposo, `tomato` al hover). No es rojo chillón: comunica "eliminar" por el icono + el terracota de la app al interactuar.
- Al click (`discard()`):
  1. Si no hay `hash`, no hace nada.
  2. `const entry = recipesStore.remove(hash)` (guarda la entrada para undo).
  3. `discarded = true` → la card se oculta (raíz con `v-show="!discarded"`).
  4. `toasts.notify('Receta descartada', 'info', 6000, { label: 'Deshacer', onClick })` donde `onClick` hace `discarded = false` + `recipesStore.restore(entry)`.
  5. Emite evento `discard` con el hash.
- La ocultación local (`v-show`) es lo que hace desaparecer la card en el chat; en las listas el `v-for` del store la desmonta automáticamente al borrarla.

### `RecipeDetailView.vue` (modificar)
- Escucha `@discard` → `router.back()` (la receta ya no existe; mejor volver que mostrar "no encontrada").

### `ChatMessage.vue` (sin cambios)
- La card se oculta sola (`v-show`) al descartar; el texto del mensaje se conserva.

## API
- Sin cambios de backend.

## Boundaries
- Verificar `npm run type-check` y `npm run test` antes de cerrar.
- No tocar backend.
- No cambiar shape de `SavedRecipe` (si se hace → key `souschef.recipes.v2` + limpieza).

## Testing (vitest)
- `stores/recipes.test.ts`: `remove` borra, persiste y devuelve la entrada; hash inexistente → `undefined`; `restore` re-inserta conservando `favorited`/`cookedAt`/`createdAt`.
- `RecipeCard.test.ts`: el botón `discard` existe; al click elimina del store, emite `discard` y muestra el toast con "Deshacer"; click en "Deshacer" restaura la receta y cierra el toast; la card se oculta tras descartar.
- `ToastStack.test.ts` (nuevo): renderiza el botón de acción y al click ejecuta `onClick` y cierra el toast.

## Success Criteria
- Toda card de receta (chat, lista y detalle) muestra el botón de papelera.
- Click → la receta desaparece del chat, de `/recetas` y de `localStorage`.
- El toast "Deshacer" restaura la receta exactamente (favorita, cocinada, fecha original).
- El detalle vuelve atrás al descartar.
- `npm run type-check` y `npm run test` en verde; cero cambios backend.

## Open Questions
- (Resuelto) Contextos: todos. En chat la card desaparece del mensaje. UX: borrado instantáneo + toast undo. Alcance: borra todo, incluso favoritas. Color: neutro → `tomato` al hover (coherente con la app).
