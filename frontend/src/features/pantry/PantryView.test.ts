import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { useToastsStore } from '../../stores/toasts'
import type { Ingredient } from '../../types'
import PantryView from './PantryView.vue'
import * as api from '../../lib/api'

vi.mock('../../lib/api', () => ({
  fetchIngredients: vi.fn(),
  createIngredient: vi.fn(),
  updateIngredient: vi.fn(),
  deleteIngredient: vi.fn(),
  cookRecipe: vi.fn(),
}))

const mockedApi = vi.mocked(api)

const items: Ingredient[] = [
  { id: 1, nombre: 'Tomate', cantidad: 3, unidad: 'piezas', categoria: 'verduras' },
  { id: 2, nombre: 'Atún', cantidad: 2, unidad: 'latas', categoria: 'proteínas' },
]

const ModalStub = {
  name: 'AppModal',
  props: { title: String },
  emits: ['close'],
  template: `
    <div data-test="modal">
      <p data-test="modal-title">{{ title }}</p>
      <slot />
    </div>
  `,
}

function mountView() {
  return mount(PantryView, {
    global: { stubs: { AppModal: ModalStub } },
  })
}

function toasts() {
  return useToastsStore().toasts.map((t) => t.message)
}

describe('PantryView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedApi.fetchIngredients.mockResolvedValue(items)
    mockedApi.createIngredient.mockResolvedValue({ ...items[0], id: 99 })
    mockedApi.updateIngredient.mockResolvedValue(items[0])
    mockedApi.deleteIngredient.mockResolvedValue()
  })

  it('muestra los ingredientes de la despensa', async () => {
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('Tomate')
    expect(wrapper.text()).toContain('Atún')
  })

  it('abre el modal de edición al pulsar Editar', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Editar')!
      .trigger('click')
    const modal = wrapper.find('[data-test="modal"]')
    expect(modal.text()).toContain('Editar ingrediente')
    expect(modal.text()).toContain('Guardar cambios')
    const input = modal.find('input[type="text"]').element as HTMLInputElement
    expect(input.value).toBe('Tomate')
  })

  it('muestra un toast al guardar un ingrediente nuevo', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((b) => b.text() === '+ Agregar ingrediente')!
      .trigger('click')
    const modal = wrapper.find('[data-test="modal"]')
    await modal.find('input[type="text"]').setValue('Champiñones')
    await modal.find('input[type="number"]').setValue(250)
    await modal.find('form').trigger('submit')
    await flushPromises()
    expect(mockedApi.createIngredient).toHaveBeenCalledWith(
      expect.objectContaining({ nombre: 'Champiñones', cantidad: 250 }),
    )
    expect(toasts()).toContain('Ingrediente agregado')
    expect(wrapper.find('[data-test="modal"]').exists()).toBe(false)
  })

  it('muestra un toast al actualizar un ingrediente', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Editar')!
      .trigger('click')
    const modal = wrapper.find('[data-test="modal"]')
    await modal.find('form').trigger('submit')
    await flushPromises()
    expect(mockedApi.updateIngredient).toHaveBeenCalledWith(1, expect.anything())
    expect(toasts()).toContain('Ingrediente actualizado')
  })

  it('confirma el borrado en un modal y muestra un toast', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Eliminar')!
      .trigger('click')
    const modal = wrapper.find('[data-test="modal"]')
    expect(modal.text()).toContain('Eliminar ingrediente')
    expect(modal.text()).toContain('¿Eliminar "Tomate"')
    await modal
      .findAll('button')
      .find((b) => b.text() === 'Eliminar')!
      .trigger('click')
    await flushPromises()
    expect(mockedApi.deleteIngredient).toHaveBeenCalledWith(1)
    const toast = useToastsStore().toasts.find((t) => t.message === 'Ingrediente eliminado')
    expect(toast?.type).toBe('error')
  })
})
