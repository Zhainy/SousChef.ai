# Spec: Recetas — Vista, Detalle, Favoritos y Receta del Día

## Objective
Funcionalidad frontend-only que da vida a las recetas generadas en el chat:
1. La card de receta del chat tiene un botón **"Ver receta"** (y la card es clicable) → navega a la vista detalle `/recetas/:hash`.
2. Cada card de receta tiene un botón corazón para marcarla como favorita.
3. Nueva vista `/recetas` con tres secciones: **Receta del día**, **Recetas generadas hoy** y **Favoritas**.
4. El stock de la despensa solo se descuenta al preparar una receta desde el detalle (click en **"Cocinar receta"**); esa receta se convierte en la **receta del día**.

## Scope
- **Frontend únicamente**: no hay cambios de esquema de BD ni endpoints nuevos. La imagen ya se sirve en `/static/recipes/{hash}.png` (mismo origen), el `hash` es estable y `recipe.image_url` llega siempre `null` (la URL real viaja en el evento `recipe_image`).

## Tech Stack
- Vue 3 (`<script setup lang="ts">`), Pinia, Vue Router, Tailwind v4, vitest. Persistencia manual en `localStorage` (sin plugin).

## Data Model (`src/types.ts`)
```ts
interface SavedRecipe {
  hash: string
  recipe: Recipe
  imageUrl: string | null
  favorited: boolean
  createdAt: string  // ISO — día en que se generó en el chat
  cookedAt: string | null  // ISO — última vez que se cocinó con éxito; null si nunca
}
```
- Clave `localStorage`: `souschef.recipes.v1`.
- Upsert por `hash`: si la receta ya existe se conservan `createdAt`, `favorited` y `cookedAt`.

## Routing (`src/router/index.ts`)
- `/recetas` → `features/recipes/RecipesView.vue` (lista con secciones)
- `/recetas/:hash` → `features/recipes/RecipeDetailView.vue` (detalle)
- NavBar: item pill "Recetas" entre "Despensa" y "Asistente" (mismo patrón `RouterLink` + `active-class`).

## Store (`src/stores/recipes.ts`, patrón de `pantry.ts`)
Estado y acciones:
- `saved: ref<SavedRecipe[]>` — hidratado desde `localStorage` al iniciar; `persist()` tras cada mutación.
- `save(recipe: Recipe, imageUrl: string | null)` — upsert por `hash`; preserva `favorited`/`createdAt`/`cookedAt` si ya existe.
- `updateImage(hash, url)` — actualiza `imageUrl` cuando llega el evento `recipe_image`.
- `toggleFavorite(hash)` — invierte `favorited`.
- `markCooked(hash)` — setea `cookedAt = now`. Solo se llama tras cocinar con éxito (`result.ok`).
- `getByHash(hash)` — look-up para el detalle.

Computeds:
- `generadasHoy` — recetas con `createdAt` del día actual, ordenadas por fecha desc (generadas en el chat hoy, se cocinen o se descarten).
- `favoritas` — todas las marcadas con corazón, de cualquier día.
- `delDia` — la receta más reciente con `cookedAt` de hoy; `null` si hoy no se cocinó ninguna.

Captura desde el chat:
- `watch` (deep) sobre `chatStore.messages`: al aparecer `entry.recipe` → `save(recipe, null)`; al llegar `entry.imageUrl` → `updateImage(hash, url)`. Desacoplado del store de chat y maneja el timing de `recipe_image`.

Limpieza:
- Al hidratar, se descartan recetas no favoritas con más de 7 días de antigüedad (por `createdAt`).

## Componentes
- `RecipeCard.vue` (modificar) — se reutiliza en chat, lista y detalle. Props nuevas: `favorited: boolean` y `showCook: boolean` (default `false`).
  - Botón corazón que llama `toggleFavorite(hash)` con `@click.stop` (no navega). Visible en todos los modos.
  - **Chat** (`showCook=false`): botón **"Ver receta"** → `router.push('/recetas/' + hash)`; la card también es clicable → detalle. No cocina.
  - **Lista `/recetas`** (`showCook=false`): la card es solo clicable (sin botón) → detalle.
  - **Detalle `/recetas/:hash`** (`showCook=true`): card completa con sus ingredientes y botón **"Cocinar receta"** (único punto de cocción). En `cook()`: tras `store.cook()` con `result.ok` → `recipesStore.markCooked(hash)`.
- `RecipesView.vue`: cabecera + tabs (Receta del día, Generadas hoy, Favoritas) que montan/desmontan la sección activa (`v-if`, una a la vez, sin `display:none`); grid de `RecipeCard` (solo clicable), cada sección con estado vacío propio.
- `RecipeDetailView.vue`: barra superior "← Volver", título, botón corazón y `RecipeCard` completo con `showCook`; si `getByHash` no encuentra la receta → estado "receta no encontrada".

## API
- Sin cambios de backend.

## Boundaries
- Verificar `npm run type-check` y `npm run test` antes de cerrar.
- No tocar backend.
- Cambios de shape de `SavedRecipe` → nueva versión de key (`souschef.recipes.v2`) + limpieza.

## Testing (vitest)
- `stores/recipes.test.ts`: upsert preservando `favorited`/`createdAt`/`cookedAt`; `toggleFavorite`; `markCooked` convierte la receta en `delDia` (y una cocinada ayer no lo es); `delDia` determinista con varias recetas del día; `generadasHoy` filtra por fecha; estado vacío; persistencia localStorage; prune de no favoritas >7 días.
- `RecipeCard.test.ts`: en modo chat el botón dice "Ver receta" y navega sin cocinar; corazón llama `toggleFavorite` sin navegar; la card clicable navega a `/recetas/:hash`; en modo detalle el botón "Cocinar receta" descuenta stock y llama `markCooked` con `result.ok`.
- `RecipesView.test.ts`: renderiza los tabs; por defecto solo se monta la sección "Receta del día"; al cambiar de tab se desmonta la anterior y se monta la nueva (una a la vez); vacíos por tab.
- `RecipeDetailView.test.ts`: muestra la receta por hash; estado no encontrado.

## Success Criteria
- "Ver receta" / click en una card del chat → `/recetas/:hash` con la receta completa e imagen.
- El corazón marca/desmarca favorito y persiste tras recargar.
- `/recetas` muestra Receta del día (la cocinada hoy), Recetas generadas hoy y Favoritas; sus cards son solo clicables.
- En el detalle, "Cocinar receta" descuenta stock y esa receta pasa a ser la receta del día.
- Cero cambios backend; tests frontend verdes.

## Open Questions
- (Resuelto) Persistencia: localStorage. Receta del día: receta cocinada hoy (solo descuenta stock la receta que se va a preparar). Generadas: las del chat del mismo día, aunque se descarten. Click: vista detalle `/recetas/:hash`.
