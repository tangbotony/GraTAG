import type { Article } from '~/pages/document/[id].vue'

export interface QuoteEditor {
  key: number
  title?: string
  href?: string
  host?: string
  description: string[]
}

export const quoteState = reactive<{
  quotes: QuoteEditor[]
  currentQuote: null | QuoteEditor
}>({
  quotes: [],
  currentQuote: null,
})

export function resetQuoteState() {
  quoteState.quotes = []
  quoteState.currentQuote = null
}

const updateQuotesByHtml = useDebounceFn((html: string, currentArticle: Article) => {
  const tempDiv = document.createElement('div')

  tempDiv.innerHTML = html

  const supElement = tempDiv.querySelectorAll('span[data-type="quote"]') as NodeListOf<HTMLElement>
  const quotesSet = new Map<string, string[]>()
  const quotes = Array.from(supElement).filter((item) => {
    if (!item.dataset.index)
      return false
    if (quotesSet.has(item.dataset.index)) {
      const all_descs = quotesSet.get(item.dataset.index)!
      const descs = item.dataset.description!.split('|||')
      descs.forEach((desc) => {
        if (!all_descs.includes(desc))
          all_descs.push(desc)
      })
      return false
    }
    else {
      const descs = item.dataset.description!.split('|||')
      quotesSet.set(item.dataset.index, descs)
      return true
    }
  })
  quoteState.quotes = quotes.map((item) => {
    let host = ''
    try {
      host = new URL(item.dataset.href!).host
    }
    catch (error) {

    }
    const key = Number(item.dataset.index)

    const description = quotesSet.get(item.dataset.index!) || []
    if (item.dataset.href) {
      const content = currentArticle.referenceContent.get(item.dataset.href)
      if (content) {
        description.sort((a, b) => {
          const indexA = content.indexOf(a)
          const indexB = content.indexOf(b)
          return indexA - indexB
        })
      }
    }

    return {
      key,
      title: item.dataset.title,
      href: item.dataset.href,
      host,
      description,
    }
  }).sort((a, b) => a.key - b.key)
}, 300)

export {
  updateQuotesByHtml,
}
