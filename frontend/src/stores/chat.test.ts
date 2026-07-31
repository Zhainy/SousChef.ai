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

async function* textOnlyStream() {
  yield { event: 'token', data: { delta: 'Solo ' } }
  yield { event: 'token', data: { delta: 'texto.' } }
  yield { event: 'done', data: { message: 'Solo texto.' } }
}

async function* recipeOnlyStream() {
  yield {
    event: 'recipe',
    data: {
      nombre: 'Pollo al limón',
      ingredientes: [{ nombre: 'pollo', cantidad: 300 }],
      hash: 'abc123',
      image_url: null,
    },
  }
  yield { event: 'recipe_image', data: { hash: 'abc123', image_url: '/static/x.png' } }
  yield { event: 'done', data: { message: '' } }
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

  it('forceRecipe adjunta la card al mensaje existente sin crear mensajes', async () => {
    mockedStream.mockReturnValueOnce(textOnlyStream())
    const store = useChatStore()
    await store.send('hola')
    expect(store.messages).toHaveLength(2)
    expect(store.messages[1].content).toBe('Solo texto.')
    expect(store.messages[1].recipe).toBeNull()

    mockedStream.mockReturnValueOnce(recipeOnlyStream())
    await store.forceRecipe()
    expect(store.messages).toHaveLength(2)
    const last = store.messages[1]
    expect(last.recipe?.nombre).toBe('Pollo al limón')
    expect(last.imageUrl).toBe('/static/x.png')
    expect(last.imagePending).toBe(false)
    expect(store.streaming).toBe(false)
    const body = mockedStream.mock.calls[1][1] as { force_recipe?: boolean }
    expect(body.force_recipe).toBe(true)
  })

  it('forceRecipe no hace nada si el último mensaje ya tiene receta', async () => {
    mockedStream.mockReturnValue(genStream())
    const store = useChatStore()
    await store.send('hola')
    await store.forceRecipe()
    expect(mockedStream).toHaveBeenCalledTimes(1)
  })

  it('forceRecipe no hace nada si el último mensaje es del usuario', async () => {
    mockedStream.mockReturnValue(textOnlyStream())
    const store = useChatStore()
    await store.send('hola')
    store.messages.push({
      id: 99,
      role: 'user',
      content: '¿y la receta?',
      recipe: null,
      imageUrl: null,
      imagePending: false,
      toolStatus: null,
      error: null,
    })
    await store.forceRecipe()
    expect(mockedStream).toHaveBeenCalledTimes(1)
  })

  it('forceRecipe no hace nada sin contenido en el último mensaje', async () => {
    const store = useChatStore()
    store.messages.push({
      id: 1,
      role: 'assistant',
      content: '',
      recipe: null,
      imageUrl: null,
      imagePending: false,
      toolStatus: null,
      error: null,
    })
    await store.forceRecipe()
    expect(mockedStream).not.toHaveBeenCalled()
  })

  it('forceRecipe guarda el error cuando el stream falla', async () => {
    mockedStream.mockReturnValueOnce(textOnlyStream())
    const store = useChatStore()
    await store.send('hola')
    mockedStream.mockReturnValueOnce(
      (async function* () {
        throw new Error('conexión perdida')
      })(),
    )
    await store.forceRecipe()
    expect(store.messages[1].error).toBe('conexión perdida')
    expect(store.streaming).toBe(false)
  })

  it('forceRecipe aplica el evento error del backend', async () => {
    mockedStream.mockReturnValueOnce(textOnlyStream())
    const store = useChatStore()
    await store.send('hola')
    mockedStream.mockReturnValueOnce(
      (async function* () {
        yield { event: 'error', data: { message: 'cuota agotada' } }
      })(),
    )
    await store.forceRecipe()
    expect(store.messages[1].error).toBe('cuota agotada')
  })

  it('forceRecipe muestra error si el turno no devuelve receta', async () => {
    mockedStream.mockReturnValueOnce(textOnlyStream())
    const store = useChatStore()
    await store.send('hola')
    mockedStream.mockReturnValueOnce(
      (async function* () {
        yield { event: 'done', data: { message: '' } }
      })(),
    )
    await store.forceRecipe()
    expect(store.messages[1].error).toContain('No pude convertir')
  })
})
