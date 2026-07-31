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

  it('incluye latas como unidad disponible', () => {
    const wrapper = mount(IngredientForm, { props: { initial: null } })
    const options = wrapper
      .findAll('select option')
      .map((o) => o.text())
    expect(options).toContain('latas')
  })

  it('muestra gramos por unidad para unidades de envase', async () => {
    const wrapper = mount(IngredientForm, { props: { initial: null } })
    await wrapper.find('select').setValue('g')
    expect(wrapper.text()).not.toContain('Gramos por unidad')
    await wrapper.find('select').setValue('latas')
    expect(wrapper.text()).toContain('Gramos por unidad')
    await wrapper.find('input[placeholder="Ej: 140"]').setValue(140)
    await wrapper.find('input[type="text"]').setValue('Atún')
    await wrapper.find('form').trigger('submit')
    const payload = wrapper.emitted('saved')?.[0]?.[0] as {
      gramos_por_unidad: number | null
    }
    expect(payload.gramos_por_unidad).toBe(140)
  })

  it('envía gramos_por_unidad nulo si no aplica', async () => {
    const wrapper = mount(IngredientForm, { props: { initial: null } })
    await wrapper.find('input[type="text"]').setValue('Sal')
    await wrapper.find('form').trigger('submit')
    const payload = wrapper.emitted('saved')?.[0]?.[0] as {
      gramos_por_unidad: number | null
    }
    expect(payload.gramos_por_unidad).toBeNull()
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
