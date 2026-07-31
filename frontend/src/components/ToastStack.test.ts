import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ToastStack from './ToastStack.vue'
import { useToastsStore } from '../stores/toasts'

describe('ToastStack', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('sin acción no renderiza botón extra', () => {
    const store = useToastsStore()
    store.notify('Hola')
    const wrapper = mount(ToastStack)
    expect(wrapper.find('[data-test="toast-action"]').exists()).toBe(false)
  })

  it('renderiza la acción y al click ejecuta onClick y cierra el toast', () => {
    const store = useToastsStore()
    const onClick = vi.fn()
    store.notify('Receta descartada', 'info', 6000, { label: 'Deshacer', onClick })
    const wrapper = mount(ToastStack)
    const action = wrapper.find('[data-test="toast-action"]')
    expect(action.exists()).toBe(true)
    expect(action.text()).toBe('Deshacer')
    action.trigger('click')
    expect(onClick).toHaveBeenCalledTimes(1)
    expect(store.toasts).toHaveLength(0)
  })
})
