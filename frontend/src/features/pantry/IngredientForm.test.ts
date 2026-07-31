import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import IngredientForm from './IngredientForm.vue'

describe('IngredientForm', () => {
  it('emits saved with normalized payload', async () => {
    const wrapper = mount(IngredientForm, { props: { initial: null } })
    await wrapper.find('input[type="text"]').setValue('  Pollo  ')
    await wrapper.find('input[type="number"]').setValue(2)
    await wrapper.find('form').trigger('submit')
    const payload = wrapper.emitted('saved')?.[0]?.[0] as {
      nombre: string
      cantidad: number
    }
    expect(payload.nombre).toBe('Pollo')
    expect(payload.cantidad).toBe(2)
  })

  it('shows validation error when nombre is empty', async () => {
    const wrapper = mount(IngredientForm, { props: { initial: null } })
    await wrapper.find('form').trigger('submit')
    expect(wrapper.text()).toContain('El nombre es obligatorio')
    expect(wrapper.emitted('saved')).toBeFalsy()
  })

  it('prefills fields when editing', () => {
    const wrapper = mount(IngredientForm, {
      props: {
        initial: {
          id: 1,
          nombre: 'Tomate',
          cantidad: 3,
          unidad: 'piezas',
          categoria: 'verduras',
        },
      },
    })
    const input = wrapper.find('input[type="text"]').element as HTMLInputElement
    expect(input.value).toBe('Tomate')
    expect(wrapper.find('form').text()).toContain('Guardar cambios')
  })
})
