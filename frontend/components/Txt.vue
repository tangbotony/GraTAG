<script lang="ts" setup>
const props = defineProps<{
  currentDesc: string
  descs: string[]
  id: string
  scroller: HTMLElement | null
}>()

const { currentDesc, descs, id, scroller } = toRefs(props)
const contentDom = ref()
const contentHtml = ref('')
let originData = ''
watch(id, async (value: string) => {
  if (!value)
    return

  const txtdata = await useGetDocSearch(value, 'txt')
  if (!txtdata.data.value)
    return

  if (descs.value.length === 0)
    return

  originData = txtdata.data.value
  highlight(originData)
  await nextTick()

  if (currentDesc.value)
    go(currentDesc.value)
}, { immediate: true })

watch(currentDesc, (value: string) => {
  if (value)
    go(value)
})

watch(descs, (value: string[]) => {
  if (originData)
    highlight(originData)
})

function highlight(content: string) {
  descs.value.forEach((desc: string) => {
    content = safeReplace(content, desc, `<span class="quote-window-highlight2">${desc}</span>`)
  })
  contentHtml.value = content
}

function go(current: string) {
  const parent = contentDom.value as HTMLElement
  if (!parent)
    return
  const doms = parent.querySelectorAll('.quote-window-highlight2')
  if (doms) {
    const topData: number[] = []
    const heightData: number[] = []
    Array.from(doms).forEach((dom) => {
      if ((dom.textContent && current.trim().includes(dom.textContent)) || (dom.textContent && current.includes(dom.textContent))) {
        topData.push((dom as HTMLElement).offsetTop)
        heightData.push((dom as HTMLElement).offsetHeight)
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
</script>

<template>
  <div ref="contentDom" v-html="contentHtml" />
</template>
