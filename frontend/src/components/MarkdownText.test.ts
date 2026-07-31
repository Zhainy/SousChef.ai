import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import MarkdownText from './MarkdownText.vue'

describe('MarkdownText', () => {
  it('renderiza negritas, listas y bloques de código', () => {
    const wrapper = mount(MarkdownText, {
      props: {
        text: 'Te sugiero **Arroz con atún**.\n\n```\n1 lata de atún\n```',
      },
    })
    expect(wrapper.find('strong').text()).toBe('Arroz con atún')
    expect(wrapper.find('pre code').exists()).toBe(true)
    expect(wrapper.text()).toContain('1 lata de atún')
  })

  it('elimina scripts maliciosos', () => {
    const wrapper = mount(MarkdownText, {
      props: { text: 'Hola <script>alert(1)</script>' },
    })
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.text()).toContain('Hola')
  })
})
