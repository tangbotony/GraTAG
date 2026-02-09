<script setup lang="ts">
import Token from '~/lib/token'
import PDF from '~/lib/pdf'

export interface PdfHightArea {
  page: number
  poly: [number, number, number, number]
}

const props = defineProps<{
  url: string
  highlightArea: PdfHightArea[] | null
  currentHighlightArea: PdfHightArea | null
}>()

const { highlightArea, url, currentHighlightArea } = toRefs(props)
const isEnv = import.meta.env.VITE_ENV === 'sit'
const token = new Token(isEnv ? 'dev' : 'prod')
const iframeContainerRef = ref()

let pdf: PDF | null = null

onMounted(async () => {
  pdf = new PDF(iframeContainerRef.value, token.token)
  await pdf.init()
  await pdf.open(url.value)
  if (highlightArea.value && currentHighlightArea.value) {
    await pdf.next(currentHighlightArea.value, highlightArea.value!)
    const value = currentHighlightArea.value
    const index = highlightArea.value.findIndex((i) => {
      if ((i.page === value?.page)
      && (i.poly[0] === value?.poly[0])
      && (i.poly[1] === value?.poly[1])
    && (i.poly[2] === value.poly[2])
  && (i.poly[3] === value.poly[3]))
        return true
      return false
    })
    pdf.highlight(index, highlightArea.value)
  }
})

watch(url, async () => {
  if (pdf?.isInit) {
    pdf.open(url.value)
    if (highlightArea.value && currentHighlightArea.value) {
      await pdf.next(currentHighlightArea.value, highlightArea.value!)
      const value = currentHighlightArea.value
      const index = highlightArea.value.findIndex((i) => {
        if ((i.page === value?.page)
      && (i.poly[0] === value?.poly[0])
      && (i.poly[1] === value?.poly[1])
    && (i.poly[2] === value.poly[2])
  && (i.poly[3] === value.poly[3]))
          return true
        return false
      })
      pdf.highlight(index, highlightArea.value)
    }
  }
})

watch(currentHighlightArea, async (value) => {
  if (value && highlightArea.value) {
    const index = highlightArea.value.findIndex((i) => {
      if ((i.page === value?.page)
      && (i.poly[0] === value?.poly[0])
      && (i.poly[1] === value?.poly[1])
    && (i.poly[2] === value.poly[2])
  && (i.poly[3] === value.poly[3]))
        return true
      return false
    })

    if (index !== -1) {
      await pdf?.next(highlightArea.value[index], highlightArea.value)
      pdf?.highlight(index, highlightArea.value)
    }
  }
})

onBeforeUnmount(() => {
  pdf?.close()
})
</script>

<template>
  <div ref="iframeContainerRef" class="w-full h-full relative flex items-center justify-center" />
</template>

<style lang="scss" scoped>
</style>
