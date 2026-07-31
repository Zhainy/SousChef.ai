import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import RecipeDetailView from './RecipeDetailView.vue'
import { useRecipesStore } from '../../stores/recipes'
import type { Recipe } from '../../types'

const back = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), back }),
  useRoute: () => ({ params: { hash: 'abc123' } }),
}))

function recipe(): Recipe {
  return {
    nombre: 'Pollo al limón',
    ingredientes: [{ nombre: 'pollo', cantidad: 300, unidad: 'g' }],
    hash: 'abc123',
  }
}

describe('RecipeDetailView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    back.mockReset()
  })

  it('muestra la receta completa con botón cocinar', () => {
    const store = useRecipesStore()
    store.save(recipe(), '/static/abc123.png')
    const wrapper = mount(RecipeDetailView)
    expect(wrapper.text()).toContain('Pollo al limón')
    expect(wrapper.find('[data-test="cook"]').exists()).toBe(true)
    expect(wrapper.find('img').attributes('src')).toBe('/static/abc123.png')
  })

  it('muestra "no encontrada" cuando el hash no existe', () => {
    const wrapper = mount(RecipeDetailView)
    expect(wrapper.text()).toContain('Receta no encontrada')
    expect(wrapper.find('[data-test="cook"]').exists()).toBe(false)
  })

  it('volver navega hacia atrás', async () => {
    const store = useRecipesStore()
    store.save(recipe(), null)
    const wrapper = mount(RecipeDetailView)
    await wrapper.find('[data-test="back"]').trigger('click')
    expect(back).toHaveBeenCalled()
  })
})
