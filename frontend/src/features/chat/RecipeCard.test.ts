import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import RecipeCard from './RecipeCard.vue'
import { ApiError, cookRecipe } from '../../lib/api'

vi.mock('../../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api')>()
  return {
    ...actual,
    cookRecipe: vi.fn(),
    fetchIngredients: vi.fn().mockResolvedValue([]),
  }
})

const mockedCook = vi.mocked(cookRecipe)

const recipe = {
  nombre: 'Pollo al limón',
  resumen: 'Rápido y fresco',
  tiempo_minutos: 20,
  ingredientes: [
    { nombre: 'pollo', cantidad: 300, unidad: 'g' },
    { nombre: 'limón', cantidad: 1, unidad: 'pieza' },
  ],
  instrucciones: '1. Cocinar el pollo.\n2. Añadir el limón.',
}

function mountCard(props: Record<string, unknown> = {}) {
  return mount(RecipeCard, {
    props: { recipe, imageUrl: null, imagePending: false, ...props },
  })
}

describe('RecipeCard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedCook.mockReset()
  })

  it('muestra nombre, tiempo e ingredientes', () => {
    const wrapper = mountCard()
    expect(wrapper.text()).toContain('Pollo al limón')
    expect(wrapper.text()).toContain('~20 min')
    expect(wrapper.text()).toContain('pollo')
    expect(wrapper.text()).toContain('300 g')
    expect(wrapper.text()).toContain('1 pieza')
  })

  it('muestra las instrucciones como lista numerada', async () => {
    const wrapper = mountCard()
    expect(wrapper.find('ol').exists()).toBe(false)
    await wrapper.find('button').trigger('click')
    const steps = wrapper.findAll('ol li')
    expect(steps).toHaveLength(2)
    expect(steps[0].text()).toBe('Cocinar el pollo.')
    expect(steps[1].text()).toBe('Añadir el limón.')
  })

  it('muestra spinner mientras se genera la imagen', () => {
    const wrapper = mountCard({ imagePending: true, imageUrl: null })
    expect(wrapper.text()).toContain('Generando imagen…')
    expect(wrapper.find('img').exists()).toBe(false)
  })

  it('muestra la imagen cuando está lista', () => {
    const wrapper = mountCard({ imagePending: false, imageUrl: '/static/x.png' })
    expect(wrapper.find('img').attributes('src')).toBe('/static/x.png')
  })

  it('cocina y marca la receta como cocinada', async () => {
    mockedCook.mockResolvedValue({
      ok: true,
      descontados: [{ nombre: 'pollo', cantidad: 300, unidad: 'g' }],
      faltantes: [],
    })
    const wrapper = mountCard()
    await wrapper.find(`[data-test="cook"]`).trigger("click")
    await flushPromises()
    expect(mockedCook).toHaveBeenCalled()
    expect(wrapper.text()).toContain('¡Cocinada!')
  })

  it('muestra los faltantes ante un 409', async () => {
    mockedCook.mockRejectedValue(
      new ApiError(409, {
        detail: {
          faltantes: [{ nombre: 'pollo', motivo: 'stock insuficiente' }],
        },
      }),
    )
    const wrapper = mountCard()
    await wrapper.find(`[data-test="cook"]`).trigger("click")
    await flushPromises()
    expect(wrapper.text()).toContain('No hay suficiente stock')
    expect(wrapper.text()).toContain('pollo')
    expect(wrapper.text()).toContain('stock insuficiente')
  })
})
