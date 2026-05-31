<script setup lang="ts">
import { QaMode, useQaStore } from '~/store/qa'
import type { PdfHightArea } from '~/components/Pdf.vue'

const qaStore = useQaStore()
const { qaState } = storeToRefs(qaStore)
const visible = ref(false)
const position = ref({
  top: 0,
  left: 0,
  bottom: 0,
  right: 0,
})
const triggerRef = ref<any>({
  getBoundingClientRect() {
    return position.value
  },
})
interface DocCurrentRef { _id: string; docName: string; refId: string; pairId: string; collId: string }

const currentNews = ref<RefPage | DocCurrentRef | null>(null)

let showTimeoutId: number | undefined
let currTarget: HTMLElement | null = null

function visibleQaContent(event: MouseEvent, target: HTMLElement) {
  if (qaState.value.mode === QaMode.WEB) {
    const coll_id = target.dataset.collId as string
    const collection = qaState.value.collection.find(i => i.id === coll_id)
    if (!collection)
      return
    const pair = collection.pairs.find(i => i._id === collection.curPairId)
    if (!pair || !pair.qa_info)
      return

    const list = pair.qa_info.ref_pages_list
    const new_ = list.find(i => i._id === target.dataset.id)
    if (!new_)
      return
    currentNews.value = new_
  }
  else {
    const data = qaState.value.docs.find(i => i._id === target.dataset.id)
    if (!data)
      return
    currentNews.value = {
      _id: data._id,
      docName: `${data.name}.${data.format}`,
      refId: target.dataset.refId as string,
      pairId: target.dataset.pairId as string,
      collId: target.dataset.collId as string,
    }
  }
  position.value = DOMRect.fromRect({
    width: 0,
    height: 0,
    x: event.clientX,
    y: event.clientY,
  })
  visible.value = true
}

function visibleQaTime(event: MouseEvent, target: HTMLElement) {
  const coll_id = target.dataset.collId as string
  const collection = qaState.value.collection.find(i => i.id === coll_id)
  if (!collection)
    return
  const pair = collection.pairs.find(i => i._id === collection.curPairId)
  if (!pair || !pair.qa_info)
    return

  let ref: undefined | { url: string
    title: string
    _id: string
    content: string
    icon: string
    news_id: string
  }
  pair.timeline_id?.events.forEach((event) => {
    event.event_list.forEach((i) => {
      const ids = Object.keys(i.reference_object)
      const id = ids.find(id => id === `[${target.dataset.id}]`)
      if (id) {
        ref = i.reference_object[id]
        ref._id = id
      }
    })
  })
  if (!ref)
    return

  if (!ref.icon) {
    const new_ = pair.qa_info.ref_pages_list.find(i => i._id === ref!.news_id)
    if (new_)
      ref.icon = new_.icon
  }

  currentNews.value = {
    _id: ref._id,
    title: ref.title,
    summary: ref.content,
    icon: ref.icon,
    site: new URL(ref.url).hostname,
    url: ref.url,
    content: '',
  }
  position.value = DOMRect.fromRect({
    width: 0,
    height: 0,
    x: event.clientX,
    y: event.clientY,
  })
  visible.value = true
}

useEventListener('mouseover', async (event: MouseEvent) => {
  if (!event.target)
    return
  const target = event.target as HTMLElement
  if (target && target.dataset && target.dataset.type === 'qa-content-ref') {
    currTarget = target
    showTimeoutId = window.setTimeout(() => {
      visibleQaContent(event, target)
    }, 300)
    return
  }

  if ((target.parentElement && target.parentElement.dataset && target.parentElement.dataset.type === 'qa-content-ref')) {
    currTarget = target.parentElement
    showTimeoutId = window.setTimeout(() => {
      visibleQaContent(event, target.parentElement!)
    }, 300)
    return
  }

  if (target && target.dataset && target.dataset.type === 'qa-time-ref') {
    currTarget = target
    showTimeoutId = window.setTimeout(() => {
      visibleQaTime(event, target)
    }, 300)
  }
})

useEventListener('mouseout', (event: MouseEvent) => {
  if (!event.target)
    return
  if (showTimeoutId && (event.target === currTarget || (event.target as HTMLElement).parentElement === currTarget)) {
    window.clearTimeout(showTimeoutId)
    showTimeoutId = undefined
    currTarget = null
  }
})

useEventListener('click', (event: MouseEvent) => {
  if (!event.target)
    return
  let target = event.target as HTMLElement
  if ((target?.dataset && target.dataset.type === 'qa-content-ref') || (target?.parentElement?.dataset && target.parentElement.dataset.type === 'qa-content-ref')) {
    if (target?.parentElement?.dataset && target.parentElement.dataset.type === 'qa-content-ref')
      target = target.parentElement

    if (qaState.value.mode === QaMode.WEB) {
      const coll_id = target.dataset.collId as string
      const collection = qaState.value.collection.find(i => i.id === coll_id)
      if (!collection)
        return
      const pair = collection.pairs.find(i => i._id === collection.curPairId)
      if (!pair || !pair.qa_info)
        return

      const new_ = pair.qa_info.ref_pages_list.find(i => i._id === target.dataset.id)
      if (!new_)
        return
      window.open(new_.url, '_blank')
    }
    else {
      const data = qaState.value.docs.find(i => i._id === target.dataset.id)
      if (!data)
        return

      currentNews.value = {
        _id: data._id,
        docName: `${data.name}.${data.format}`,
        refId: target.dataset.refId as string,
        pairId: target.dataset.pairId as string,
        collId: target.dataset.collId as string,
      }
      openWindow()
    }
  }

  if (target && target.dataset && target.dataset.type === 'qa-time-ref') {
    const url = target.dataset.url as string
    if (url)
      window.open(url, '_blank')
  }
})

useEventListener('scroll', () => {
  visible.value = false
}, {
  capture: true,
})

const contentRef = ref()
onClickOutside(contentRef, () => {
  visible.value = false
})

function handleClick() {
  if (qaState.value.mode === QaMode.WEB)
    window.open((currentNews.value as RefPage).url, '_blank')
  else
    openWindow()
}

const visibleWindow = ref(false)
const currentWindowContent = ref('')
const windowContent = ref<string[]>([])
// [ left, top, right, bottom]
const currentHighlightArea = ref<PdfHightArea | null>(null)
const highlightArea = ref<PdfHightArea[]>([])
const title = ref('')
const fileid = ref('')
const currentFileFormat = ref('')
function isUsePdfLoad(fileName: string) {
  return fileName.includes('pdf') || fileName.includes('docx') || fileName.includes('doc')
}
function openWindow() {
  // return
  if (!currentNews.value || !currentNews.value._id)
    return

  const data = currentNews.value as DocCurrentRef

  const collection = qaState.value.collection.find(i => i.id === data.collId)
  if (!collection)
    return
  const pair = collection.pairs.find(i => i._id === data.pairId)
  if (!pair || !pair.reference)
    return

  title.value = data.docName
  fileid.value = data._id
  const pRef = pair.reference.find(i => i._id.slice(1, -1) === data.refId)
  if (!pRef)
    return

  // if (data.docName.includes('txt'))
  //   pRef.origin_content = [pRef.origin_content]

  if (isUsePdfLoad(data.docName) && pRef.polyDto && pRef.polyDto.length > 0) {
    currentFileFormat.value = 'pdf'
    highlightArea.value = pRef.polyDto.concat()
    highlightArea.value.sort((a, b) => a.page - b.page)
    currentHighlightArea.value = highlightArea.value[0]
    visibleWindow.value = true
  }
  else if (data.docName.includes('txt') && pRef.origin_content && pRef.origin_content.length > 0) {
    currentFileFormat.value = 'txt'
    windowContent.value = pRef.origin_content
    currentWindowContent.value = pRef.origin_content[0]
    visibleWindow.value = true
  }
}

function handleWindowChange(index: number) {
  if (currentFileFormat.value === 'txt')
    currentWindowContent.value = windowContent.value[index]
  else if (currentFileFormat.value === 'pdf')
    currentHighlightArea.value = highlightArea.value[index]
}

function handleWindowClose() {
  visibleWindow.value = false
  currentNews.value = null
  currentWindowContent.value = ''
  windowContent.value = []
  title.value = ''
  fileid.value = ''
  currentHighlightArea.value = null
  highlightArea.value = []
}
</script>

<template>
  <el-tooltip
    :visible="visible"
    effect="dark"
    content="Bottom center"
    placement="bottom"
    trigger="contextmenu"
    virtual-triggering
    :virtual-ref="triggerRef"
  >
    <template #content>
      <template v-if="currentNews">
        <div ref="contentRef" class="py-[6px] w-[240px] cursor-pointer" @click="handleClick">
          <template v-if="qaState.mode === QaMode.WEB">
            <div class="text-white text-[12px] font-500 mb-[6px]">
              {{ (currentNews as RefPage).title }}
            </div>
            <div class="text-[12px] text-[rgba(255,255,255,0.55)] text-hidden-3 mb-[6px]">
              {{ (currentNews as RefPage).summary }}
            </div>
            <div class="flex items-center">
              <img v-if="(currentNews as RefPage).icon" class="w-[12px] h-[12px]" :src="(currentNews as RefPage).icon">
              <div v-else class="i-ll-earth text-[12px]  text-[#d8d8d8] mr-[4px]" />

              <div class="ml-[4px] text-[12px] text-[rgba(255,255,255,0.55)] truncate">
                {{ (currentNews as RefPage).site }}
              </div>
            </div>
          </template>
          <template v-else>
            <div class="text-white text-[12px] font-500">
              {{ (currentNews as DocCurrentRef).docName }}
            </div>
          </template>
        </div>
      </template>
    </template>
  </el-tooltip>
  <Teleport to="body">
    <QaWindow
      :visible="visibleWindow"
      :current-content="currentWindowContent"
      :contents="windowContent"
      :current-highlight-area="currentHighlightArea"
      :highlight-area="highlightArea"
      :title="title"
      :file-id="fileid"
      :format="currentFileFormat"
      @change="handleWindowChange"
      @close="handleWindowClose"
    />
  </Teleport>
</template>
