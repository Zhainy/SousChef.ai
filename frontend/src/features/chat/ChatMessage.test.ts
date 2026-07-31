import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatMessage from './ChatMessage.vue'
import type { ChatEntry } from '../../stores/chat'

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
})
