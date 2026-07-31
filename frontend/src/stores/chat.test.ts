import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useChatStore } from './chat'
import { postSseStream } from '../lib/sse'

vi.mock('../lib/sse', () => ({
  postSseStream: vi.fn(),
}))

const mockedStream = vi.mocked(postSseStream)

function events() {
  return [
    { event: 'tool_call', data: { name: 'get_inventario' } },
    { event: 'tool_result', data: { name: 'get_inventario', result: '{}' } },
    { event: 'token', data: { delta: 'Hola' } },
    { event: 'token', data: { delta: ' chef!' } },
    {
      event: 'recipe',
      data: {
        nombre: 'Pollo al limón',
        ingredientes: [{ nombre: 'pollo', cantidad: 300 }],
        hash: 'abc123',
        image_url: null,
      },
    },
    { event: 'recipe_image', data: { hash: 'abc123', image_url: '/static/x.png' } },
    { event: 'done', data: { message: 'Hola chef!' } },
  ]
}

async function* genStream() {
  for (const ev of events()) yield ev
}

describe('useChatStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedStream.mockReset()
  })

  it('acumula tokens y adjunta receta e imagen', async () => {
    mockedStream.mockReturnValue(genStream())
    const store = useChatStore()
    await store.send('hola')
    expect(store.messages).toHaveLength(2)
    const [user, assistant] = store.messages
    expect(user.role).toBe('user')
    expect(user.content).toBe('hola')
    expect(assistant.content).toBe('Hola chef!')
    expect(assistant.recipe?.nombre).toBe('Pollo al limón')
    expect(assistant.imageUrl).toBe('/static/x.png')
    expect(assistant.imagePending).toBe(false)
    expect(store.streaming).toBe(false)
  })

  it('guarda el error cuando el stream falla', async () => {
    mockedStream.mockReturnValue(
      (async function* () {
        throw new Error('conexión perdida')
      })(),
    )
    const store = useChatStore()
    await store.send('hola')
    expect(store.messages[1].error).toBe('conexión perdida')
  })

  it('no envía mensajes vacíos ni duplicados mientras streamea', async () => {
    mockedStream.mockReturnValue(genStream())
    const store = useChatStore()
    await store.send('   ')
    expect(store.messages).toHaveLength(0)
  })
})
