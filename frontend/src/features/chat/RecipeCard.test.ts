import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import RecipeCard from './RecipeCard.vue'
import { useRecipesStore } from '../../stores/recipes'
import { ApiError, cookRecipe } from '../../lib/api'

vi.mock('../../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api')>()
  return {
    ...actual,
    cookRecipe: vi.fn(),
    fetchIngredients: vi.fn().mockResolvedValue([]),
  }
})

const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
}))

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
  hash: 'abc123',
}

function mountCard(props: Record<string, unknown> = {}) {
  return mount(RecipeCard, {
    props: { recipe, imageUrl: null, imagePending: false, ...props },
  })
}

describe('RecipeCard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    mockedCook.mockReset()
    push.mockReset()
  })

  it('muestra nombre, tiempo e ingredientes', () => {
    const wrapper = mountCard()
    expect(wrapper.text()).toContain('Pollo al limón')
    expect(wrapper.text()).toContain('~20 min')
    expect(wrapper.text()).toContain('pollo')
    expect(wrapper.text()).toContain('300 g')
    expect(wrapper.text()).toContain('1 pieza')
  })

  it('registra la receta en el store al montar', () => {
    mountCard()
    const store = useRecipesStore()
    expect(store.getByHash('abc123')).toBeDefined()
  })

  it('en modo chat muestra "Ver receta" y navega al detalle sin cocinar', async () => {
    const wrapper = mountCard()
    const view = wrapper.find('[data-test="view"]')
    expect(view.exists()).toBe(true)
    expect(view.text()).toBe('Ver receta')
    expect(wrapper.find('[data-test="cook"]').exists()).toBe(false)
    await view.trigger('click')
    expect(push).toHaveBeenCalledWith({ name: 'receta-detalle', params: { hash: 'abc123' } })
    expect(mockedCook).not.toHaveBeenCalled()
  })

  it('la card clicable navega al detalle', async () => {
    const wrapper = mountCard({ showView: false })
    await wrapper.find('[data-test="card"]').trigger('click')
    expect(push).toHaveBeenCalledWith({ name: 'receta-detalle', params: { hash: 'abc123' } })
  })

  it('el corazón marca favorita sin navegar', async () => {
    const wrapper = mountCard()
    await wrapper.find('[data-test="favorite"]').trigger('click')
    const store = useRecipesStore()
    expect(store.getByHash('abc123')?.favorited).toBe(true)
    expect(push).not.toHaveBeenCalled()
  })

  it('muestra las instrucciones como lista numerada', async () => {
    const wrapper = mountCard()
    expect(wrapper.find('ol').exists()).toBe(false)
    await wrapper.find('[data-test="toggle-instructions"]').trigger('click')
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

  it('en modo detalle cocina, descuenta stock y marca cookedAt', async () => {
    mockedCook.mockResolvedValue({
      ok: true,
      descontados: [{ nombre: 'pollo', cantidad: 300, unidad: 'g' }],
      faltantes: [],
    })
    const wrapper = mountCard({ showCook: true })
    expect(wrapper.find('[data-test="view"]').exists()).toBe(false)
    await wrapper.find('[data-test="cook"]').trigger('click')
    await flushPromises()
    expect(mockedCook).toHaveBeenCalled()
    expect(wrapper.text()).toContain('¡Cocinada!')
    const store = useRecipesStore()
    expect(store.getByHash('abc123')?.cookedAt).not.toBeNull()
  })

  it('muestra mensaje amigable ante un 422', async () => {
    mockedCook.mockRejectedValue(
      new ApiError(422, [{ msg: 'Input should be greater than or equal to 1' }]),
    )
    const wrapper = mountCard({ showCook: true })
    await wrapper.find('[data-test="cook"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('La receta tiene datos inválidos')
  })

  it('muestra los faltantes ante un 409', async () => {
    mockedCook.mockRejectedValue(
      new ApiError(409, {
        detail: {
          faltantes: [
            {
              nombre: 'atún',
              motivo: 'stock insuficiente',
              detalle: 'disponible: 2 latas (≈ 280 g)',
            },
          ],
        },
      }),
    )
    const wrapper = mountCard({ showCook: true })
    await wrapper.find('[data-test="cook"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('No hay suficiente stock')
    expect(wrapper.text()).toContain('stock insuficiente')
    expect(wrapper.text()).toContain('disponible: 2 latas (≈ 280 g)')
  })
})
