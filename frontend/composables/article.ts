import type { FileType } from './api/file'

export interface Article {
  title: string
  content: string
  plainText: string
  path: [string, string][]
  referenceContent: Map<string, string>
  referenceDescs: Map<string, string[]>
  isQuote: boolean
  doc?: FileType
}

const currentArticle = reactive<Article>({
  title: '',
  content: '',
  plainText: '',
  path: [],
  referenceContent: new Map(),
  referenceDescs: new Map(),
  isQuote: false,
  doc: undefined,
})

function initArticleState() {
  currentArticle.title = ''
  currentArticle.content = ''
  currentArticle.plainText = ''
  currentArticle.path = []
  currentArticle.referenceContent = new Map()
  currentArticle.referenceDescs = new Map()
  currentArticle.isQuote = false
  currentArticle.doc = undefined
}

const isArticleInit = ref(false)

watch(() => currentArticle.isQuote, (value) => {
  if (isArticleInit.value && currentArticle.doc)
    useFileUpdate({ id: currentArticle.doc._id, is_quote: value })
})

export {
  isArticleInit,
  currentArticle,
  initArticleState,
}
