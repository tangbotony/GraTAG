<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'

const props = defineProps<{
  visibleRightSideBar: boolean
  editor: Editor
  scrollcontainer: HTMLElement
}>()

const { visibleRightSideBar } = toRefs(props)

const positionStyles = ref<null | { top: number; right: number }>(null)

let currentId: string | null = null
const currentDesc = ref('')
const currentDescs = ref<string[]>([])
function clear() {
  positionStyles.value = null
  quoteState.currentQuote = null
  currentDesc.value = ''
  if (currentId)
    props.editor.commands.setCurrentQuote(currentId, false)
  currentId = null
}

useEventListener('click', async (event: Event) => {
  event.stopPropagation()
  const target = event.target as HTMLElement
  if (target.nodeName === 'HTML' || !target)
    return

  if (target.dataset.type === 'quote') {
    const quote = quoteState.quotes.find(quote => (quote.title === target.dataset.title && quote.href === target.dataset.href))!
    if (!quote) {
      if (!target.dataset.href)
        return
      quoteState.currentQuote = {
        key: 1,
        title: target.dataset.title || '',
        href: target.dataset.href || '',
        description: currentArticle.referenceDescs.get(target.dataset.href) || [],
      }
    }
    else {
      quoteState.currentQuote = quote
    }

    const descs = target.dataset.description?.split('|||').filter(desc => !!desc)
    currentDescs.value = descs || []
    currentDesc.value = descs?.[0] || ''

    if (!currentDesc.value)
      return

    if (!positionStyles.value) {
      if (!props.visibleRightSideBar) {
        positionStyles.value = {
          top: 106,
          right: 24,
        }
      }
      else {
        positionStyles.value = {
          top: 106,
          right: 494,
        }
      }
    }

    if (target.id) {
      let dom = document.getElementById(target.id)
      const topOld = dom?.getBoundingClientRect().top || 0

      if (currentId)
        props.editor.commands.setCurrentQuote(currentId, false)

      props.editor.commands.setCurrentQuote(target.id, true)
      currentId = target.id

      await nextTick()

      dom = document.getElementById(target.id)
      const top = dom?.getBoundingClientRect().top || 0

      props.scrollcontainer.scrollBy({
        left: 0,
        top: (top! - topOld!),
        behavior: 'smooth',
      })
    }
  }
})

function handleQuoteIndex(index: number) {
  currentDescs.value = []
  const desc = quoteState.currentQuote?.description[index - 1]
  if (desc)
    currentDesc.value = desc
}

const { currentQuote } = toRefs(quoteState)
const currentQuoteIndex = computed(() => {
  const index = currentQuote.value?.description.findIndex(desc => desc === currentDesc.value) || 0
  return index + 1
})
const amount = computed(() => currentQuote.value?.description.length || 0)
const title = computed(() => currentQuote.value?.title || '')
const href = computed(() => currentQuote.value?.href || '')
</script>

<template>
  <WindowFile
    v-if="currentQuote"
    v-model:position-styles="positionStyles"
    :visible-right-side-bar="visibleRightSideBar"
    :current-index="currentQuoteIndex"
    :amount="amount"
    :title="title"
    :href="href"
    @handle-index="handleQuoteIndex"
    @clear="clear"
  >
    <DocQuoteWinContent :current-desc="currentDesc" :current-descs="currentDescs" />
  </WindowFile>
</template>

<style lang="scss" scoped>
.container {
    border-radius: 12px;
    overflow: hidden;
    background: #F3F3F3;
    border: 1px solid #DCDCDC;
    box-shadow: 0px 6px 16px 0px rgba(0, 0, 0, 0.08),0px 3px 6px -4px rgba(0, 0, 0, 0.12),0px 9px 28px 8px rgba(0, 0, 0, 0.05);
    position: absolute;
    display: flex;
    flex-direction: column;
    z-index: 100;
    pointer-events: auto;
}

.text-content {
  font-size: 16px;
  font-weight: 400;
  line-height: 26px;
  color: rgba(0, 0, 0, 0.6);
  background: #FFFFFF;
  white-space: pre-wrap;
}

.drag-v-line {
  cursor: col-resize;
}
</style>
