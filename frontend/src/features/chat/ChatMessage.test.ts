import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ChatMessage from './ChatMessage.vue'
import { useChatStore, type ChatEntry } from '../../stores/chat'

function entry(overrides: Partial<ChatEntry>): ChatEntry {
  return {
    id: 1,
    role: 'assistant',
    content: '',
    recipe: null,
    imageUrl: null,
    imagePending: false,
    toolStatus: null,
    error: null,
    ...overrides,
  }
}

describe('ChatMessage', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('muestra los puntitos animados mientras el asistente piensa', () => {
    const wrapper = mount(ChatMessage, {
      props: { entry: entry({}), pending: true },
    })
    expect(wrapper.find('[role="status"]').exists()).toBe(true)
  })

  it('no muestra los puntitos si ya hay contenido', () => {
    const wrapper = mount(ChatMessage, {
      props: { entry: entry({ content: 'Hola' }), pending: true },
    })
    expect(wrapper.find('[role="status"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Hola')
  })

  it('muestra el texto del usuario alineado a la derecha', () => {
    const wrapper = mount(ChatMessage, {
      props: { entry: entry({ role: 'user', content: '¿qué cocino?' }) },
    })
    expect(wrapper.text()).toContain('¿qué cocino?')
  })

  it('muestra "Obtener la receta" en el último mensaje de texto sin receta', () => {
    const store = useChatStore()
    const e = entry({ content: 'Puedes hacer una tortilla' })
    store.messages.push(e)
    const wrapper = mount(ChatMessage, { props: { entry: e } })
    expect(wrapper.find('[data-test="ask-recipe"]').exists()).toBe(true)
  })

  it('no muestra el botón si el mensaje ya tiene receta', () => {
    const store = useChatStore()
    const e = entry({
      content: 'Receta',
      recipe: { nombre: 'X', ingredientes: [{ nombre: 'a', cantidad: 1 }] },
    })
    store.messages.push(e)
    const wrapper = mount(ChatMessage, { props: { entry: e } })
    expect(wrapper.find('[data-test="ask-recipe"]').exists()).toBe(false)
  })

  it('no muestra el botón si el mensaje tiene error', () => {
    const store = useChatStore()
    const e = entry({ content: 'Texto', error: 'cuota agotada' })
    store.messages.push(e)
    const wrapper = mount(ChatMessage, { props: { entry: e } })
    expect(wrapper.find('[data-test="ask-recipe"]').exists()).toBe(false)
  })

  it('no muestra el botón si no es el último mensaje', () => {
    const store = useChatStore()
    const older = entry({ content: 'Texto sin receta' })
    store.messages.push(older, entry({ id: 2, content: 'Más texto' }))
    const wrapper = mount(ChatMessage, { props: { entry: older } })
    expect(wrapper.find('[data-test="ask-recipe"]').exists()).toBe(false)
  })

  it('no muestra el botón para mensajes de usuario', () => {
    const store = useChatStore()
    const e = entry({ role: 'user', content: 'hola' })
    store.messages.push(e)
    const wrapper = mount(ChatMessage, { props: { entry: e } })
    expect(wrapper.find('[data-test="ask-recipe"]').exists()).toBe(false)
  })

  it('al hacer click llama a forceRecipe', async () => {
    const store = useChatStore()
    const e = entry({ content: 'Puedes hacer una tortilla' })
    store.messages.push(e)
    const spy = vi.spyOn(store, 'forceRecipe').mockResolvedValue(undefined)
    const wrapper = mount(ChatMessage, { props: { entry: e } })
    await wrapper.find('[data-test="ask-recipe"]').trigger('click')
    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('muestra "Obteniendo receta…" mientras forceRecipe corre', async () => {
    const store = useChatStore()
    const e = entry({ content: 'Texto' })
    store.messages.push(e)
    const wrapper = mount(ChatMessage, { props: { entry: e } })
    store.streaming = true
    await nextTick()
    expect(wrapper.find('[data-test="asking-recipe"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="ask-recipe"]').exists()).toBe(false)
  })
})
