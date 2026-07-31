const CATEGORIA_STYLES: Record<string, { tag: string; dot: string }> = {
  proteínas: {
    tag: 'bg-tomato-100 text-tomato-700',
    dot: 'bg-tomato-500',
  },
  verduras: {
    tag: 'bg-basil-100 text-basil-700',
    dot: 'bg-basil-500',
  },
  frutas: {
    tag: 'bg-saffron-300/30 text-saffron-700',
    dot: 'bg-saffron-500',
  },
  lácteos: {
    tag: 'bg-sky-100 text-sky-700',
    dot: 'bg-sky-500',
  },
  granos: {
    tag: 'bg-amber-100 text-amber-700',
    dot: 'bg-amber-600',
  },
  especias: {
    tag: 'bg-purple-100 text-purple-700',
    dot: 'bg-purple-500',
  },
  otros: {
    tag: 'bg-stone-100 text-stone-600',
    dot: 'bg-stone-400',
  },
}

const FALLBACK = {
  tag: 'bg-stone-100 text-stone-600',
  dot: 'bg-stone-400',
}

export function categoriaStyle(categoria: string): { tag: string; dot: string } {
  return CATEGORIA_STYLES[categoria] ?? FALLBACK
}
