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

  it('oculta el bloque JSON de la receta del mensaje', async () => {
    const withFence = [
      ...events().filter((e) => e.event === 'token'),
      {
        event: 'recipe',
        data: {
          nombre: 'Pollo al limón',
          ingredientes: [{ nombre: 'pollo', cantidad: 300 }],
          hash: 'abc123',
          image_url: null,
        },
      },
      { event: 'recipe_image', data: { hash: 'abc123', image_url: null } },
    ]
    withFence[1] = {
      event: 'token',
      data: { delta: '\n```json\n{"nombre": "Pollo"}\n```' },
    }
    async function* gen() {
      for (const ev of withFence) yield ev
    }
    mockedStream.mockReturnValue(gen())
    const store = useChatStore()
    await store.send('hola')
    expect(store.messages[1].content).not.toContain('```json')
    expect(store.messages[1].content).toBe('Hola')
  })

  it('recorta la narrativa redundante cuando hay receta', async () => {
    const narrative = [
      ...events().filter((e) => e.event !== 'recipe_image' && e.event !== 'done'),
    ]
    narrative[2] = {
      ...narrative[2],
      data: { delta: 'Te sugiero esta receta:\n\nPasta con atún\n\nIngredientes:\n' },
    }
    narrative[3] = { ...narrative[3], data: { delta: '200 g pasta\nInstrucciones:\n...' } }
    async function* gen() {
      for (const ev of narrative) yield ev
    }
    mockedStream.mockReturnValue(gen())
    const store = useChatStore()
    await store.send('hola')
    expect(store.messages[1].recipe?.nombre).toBe('Pollo al limón')
    expect(store.messages[1].content).toBe('Te sugiero esta receta:\n\nPasta con atún')
    expect(store.messages[1].content).not.toContain('200 g pasta')
  })

  it('resalta el nombre de la receta en negritas', async () => {
    const withRecipe = [
      ...events().filter((e) => e.event !== 'recipe_image' && e.event !== 'done'),
    ]
    withRecipe[2] = { ...withRecipe[2], data: { delta: 'Hoy te sugiero hacer ' } }
    withRecipe[3] = { ...withRecipe[3], data: { delta: 'Pollo al limón, es rápido' } }
    async function* gen() {
      for (const ev of withRecipe) yield ev
    }
    mockedStream.mockReturnValue(gen())
    const store = useChatStore()
    await store.send('hola')
    expect(store.messages[1].content).toBe('Hoy te sugiero hacer **Pollo al limón**, es rápido')
  })

  it('resalta el nombre aunque la intro no coincida exacto', async () => {
    const withRecipe = [
      ...events().filter((e) => e.event !== 'recipe_image' && e.event !== 'done'),
    ]
    withRecipe[2] = {
      ...withRecipe[2],
      data: {
        delta:
          'Con los ingredientes actuales puedo hacer un budín básico con huevos. Aquí tienes la receta:',
      },
    }
    withRecipe[3] = { ...withRecipe[3], data: { delta: ' ' } }
    const recipeIdx = withRecipe.findIndex((e) => e.event === 'recipe')
    withRecipe[recipeIdx] = {
      ...withRecipe[recipeIdx]!,
      data: {
        nombre: 'Budín básico de huevos y queso',
        ingredientes: [{ nombre: 'huevo', cantidad: 2 }],
        hash: 'abc123',
        image_url: null,
      },
    }
    async function* gen() {
      for (const ev of withRecipe) yield ev
    }
    mockedStream.mockReturnValue(gen())
    const store = useChatStore()
    await store.send('hola')
    expect(store.messages[1].content).toBe(
      'Con los ingredientes actuales puedo hacer un **budín básico** con huevos. Aquí tienes la receta:',
    )
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
