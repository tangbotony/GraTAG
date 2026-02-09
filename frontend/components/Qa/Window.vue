<script lang="ts" setup>
import type { PdfHightArea } from '~/components/Pdf.vue'

const props = defineProps<{
  currentContent: string
  contents: string[]
  highlightArea: PdfHightArea[]
  currentHighlightArea: PdfHightArea | null
  title: string
  fileId: string
  visible: boolean
  format: string
}>()

const $emits = defineEmits<{
  (e: 'change', value: number): void
  (e: 'close'): void
}>()

const { currentContent, contents, fileId, visible, currentHighlightArea, highlightArea, format } = toRefs(props)

const href = computed(() => {
  return `sourceid:${fileId.value}&ext:pdf&version:v2`
})

const positionStyles = ref<null | { top: number; right: number }>(null)
const currentIndex = computed(() => {
  if (format.value === 'txt')
    return contents.value.indexOf(currentContent.value) + 1

  if (format.value === 'pdf') {
    const index = highlightArea.value.findIndex((i) => {
      if ((i.page === currentHighlightArea.value?.page)
      && (i.poly[0] === currentHighlightArea.value?.poly[0])
      && (i.poly[1] === currentHighlightArea.value?.poly[1])
    && (i.poly[2] === currentHighlightArea.value.poly[2])
  && (i.poly[3] === currentHighlightArea.value.poly[3]))
        return true
      return false
    })

    return index + 1
  }
  return -1
})
function clear() {
  positionStyles.value = null
  $emits('close')
}

function handleQuoteIndex(index: number) {
  $emits('change', index - 1)
}

watch(visible, (val) => {
  if (val) {
    if (!positionStyles.value) {
      positionStyles.value = {
        top: 106,
        right: 24,
      }
    }
  }
  else {
    positionStyles.value = null
  }
})

const amount = computed(() => {
  if (format.value === 'pdf')
    return highlightArea.value.length

  return contents.value.length
})

const baseURL = import.meta.env.VITE_API

const url = computed(() => {
  return `${baseURL}api/doc_search/${fileId.value}`
})

const scroller = ref<HTMLElement | null>(null)
</script>

<template>
  <WindowFile
    v-model:position-styles="positionStyles"
    :visible-right-side-bar="true"
    :current-index="currentIndex"
    :amount="amount"
    :title="title"
    :href="href"
    @handle-index="handleQuoteIndex"
    @clear="clear"
  >
    <div ref="scroller" class="flex-1 overflow-y-scroll px-[16px] pt-[29px] pb-[19px] text-content">
      <Pdf
        v-if="fileId && format === 'pdf'"
        :url="url"
        :current-highlight-area="currentHighlightArea" :highlight-area="highlightArea"
      />
      <Txt
        v-if="fileId && format === 'txt'"
        :id="fileId"
        :current-desc="currentContent"
        :descs="contents"
        :scroller="scroller"
      />
    </div>
  </WindowFile>
</template>

<style lang="scss" scoped>
.text-content {
  font-size: 16px;
  font-weight: 400;
  line-height: 26px;
  color: rgba(0, 0, 0, 0.6);
  background: #FFFFFF;
  white-space: pre-wrap;
}
</style>
