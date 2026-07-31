import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import RecipesView from './RecipesView.vue'
import { useRecipesStore } from '../../stores/recipes'
import type { Recipe } from '../../types'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

function recipe(hash: string, nombre: string): Recipe {
  return { nombre, ingredientes: [{ nombre: 'tomate', cantidad: 1 }], hash }
}

function seedStore(): void {
  const store = useRecipesStore()
  store.save(recipe('a', 'Receta A'), null)
  store.save(recipe('b', 'Receta B'), null)
  store.save(recipe('c', 'Receta C'), null)
  const a = store.getByHash('a')!
  a.createdAt = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
  store.toggleFavorite('a')
  store.markCooked('b')
}

describe('RecipesView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('muestra las tres pestañas', () => {
    const wrapper = mount(RecipesView)
    const tabs = wrapper.findAll('[data-test="tab"]')
    expect(tabs.map((t) => t.text())).toEqual([
      'Receta del día',
      'Generadas hoy',
      'Favoritas',
    ])
  })

  it('inicialmente solo muestra la sección de la receta del día', () => {
    seedStore()
    const wrapper = mount(RecipesView)
    expect(wrapper.text()).toContain('Receta B')
    expect(wrapper.text()).not.toContain('Receta A')
    expect(wrapper.text()).not.toContain('Receta C')
  })

  it('al cambiar de pestaña se desmonta la anterior y se muestra la nueva', async () => {
    seedStore()
    const wrapper = mount(RecipesView)
    const tabs = wrapper.findAll('[data-test="tab"]')
    await tabs[1].trigger('click')
    expect(wrapper.text()).toContain('Receta C')
    expect(wrapper.text()).not.toContain('Receta A')
    await tabs[2].trigger('click')
    expect(wrapper.text()).toContain('Receta A')
    expect(wrapper.text()).not.toContain('Receta C')
  })

  it('ninguna sección muestra botón cocinar', () => {
    seedStore()
    const wrapper = mount(RecipesView)
    expect(wrapper.find('[data-test="cook"]').exists()).toBe(false)
  })

  it('muestra el vacío propio de cada pestaña', async () => {
    const wrapper = mount(RecipesView)
    expect(wrapper.text()).toContain('Aún no has cocinado ninguna receta hoy')
    const tabs = wrapper.findAll('[data-test="tab"]')
    await tabs[1].trigger('click')
    expect(wrapper.text()).toContain('No hay recetas generadas hoy')
    await tabs[2].trigger('click')
    expect(wrapper.text()).toContain('Marca recetas con el corazón')
  })
})
