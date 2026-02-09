<script lang="ts" setup>
const props = defineProps<{
  currentDesc: string
  currentDescs: string[]
}>()

const scroller = ref()
const pdfId = ref('')
const fileExt = ref('')
const contentDom = ref<null | HTMLElement>()
const { currentDesc, currentDescs } = toRefs(props)
const contentHtml = ref('')
const baseURL = import.meta.env.VITE_API

function getHrefParam(txt: string, params: string) {
  const paramsArray = params.split('&')
  let str = ''
  paramsArray.forEach((item: string) => {
    const [key, value] = item.split(':')
    if (key === txt)
      str = value
  })
  return str
}
watch(currentDesc, async (value: string) => {
  let content = ''
  if (quoteState.currentQuote && quoteState.currentQuote.href) {
    if (!quoteState.currentQuote.href.includes('http') && quoteState.currentQuote.href.includes('sourceid')) {
      const sourceidstr = getHrefParam('sourceid', quoteState.currentQuote.href)
      pdfId.value = sourceidstr
      fileExt.value = getHrefParam('ext', quoteState.currentQuote.href)
      const txtdata = await materialArticle(sourceidstr)
      content = txtdata.data.value ? txtdata.data.value : ''
      // content = decodeURIComponent(escape(content))
    }
    else {
      pdfId.value = ''
      fileExt.value = 'html'
      const contenttxt = currentArticle.referenceContent.get(quoteState.currentQuote.href)
      content = contenttxt || ''
    }
  }
  if (fileExt.value === 'html' || fileExt.value === 'txt') {
    if (!content)
      return []

    quoteState.currentQuote?.description.forEach((desc: string) => {
      content = content!.replaceAll(desc, `<span class="quote-window-highlight">${desc}</span>`)
    })
    contentHtml.value = content

    await nextTick()
    const doms = contentDom.value?.querySelectorAll('.quote-window-highlight')
    if (doms) {
      Array.from(doms).forEach((dom) => {
        (dom as HTMLElement).classList.remove('current')
      })
      const topData: number[] = []
      const heightData: number[] = []
      Array.from(doms).forEach((dom) => {
        if ((dom.textContent && value.trim().includes(dom.textContent)) || (dom.textContent && currentDescs.value.includes(dom.textContent))) {
          topData.push((dom as HTMLElement).offsetTop)
          heightData.push((dom as HTMLElement).offsetHeight)
          dom.classList.add('current')
        }
      })
      if (topData.length > 0) {
        const topmin = Math.min(...topData)
        const minIndex = topData.indexOf(topmin)
        scroller.value?.scroll(
          {
            top: topmin - heightData[minIndex] - 36,
            left: 0,
            behavior: 'smooth',
          },
        )
      }
    }
  }
}, { immediate: true },
)

const url = computed(() => {
  return `${baseURL}api/material/preview/${pdfId.value}?to_pdf=true`
})
</script>

<template>
  <div ref="scroller" class="flex-1 overflow-y-scroll px-[16px] pt-[29px] pb-[19px] text-content">
    <PdfOld v-if="pdfId && fileExt !== 'txt'" :url="url" :currentdesc="currentDesc" />
    <div v-else ref="contentDom" v-html="contentHtml" />
  </div>
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
