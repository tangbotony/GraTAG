<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'
import stats from '~/lib/stats'
import { collectRefContent, extraQuote, splitText, transformQuoteSumData } from '~/composables/ai/useWriting'
import { NEWS_KIND } from '~/consts/editor'

const props = defineProps<{
  editor: Editor
  scrollContainer: any
  data: any
  type: string
}>()

const $emits = defineEmits<{
  (e: 'apply'): void
  (e: 'back'): void
}>()

const { scrollContainer } = toRefs(props)
const loadingTime = computed(() => {
  if (props.data.use_trusted_website) {
    return 120
  }
  else {
    if (props.type === NEWS_KIND.Summarize)
      return 40
    else
      return 30
  }
})

const isLoading = ref(false)

const content = ref('')
const title = ref('')
const titleDom = ref()
const title_list = ref<string[]>([])

const rect = ref({ top: 0, left: 0, width: 0, height: 0 })
const visibleRect = ref(false)
const refreshIcon = ref({ top: 0, left: 0 })

const contentRange = ref({ from: 0, to: 0 })

const boxStart = ref(0)
const boxEnd = ref(0)

const isInserting = ref(false)
const isInsertTitle = ref(false)

function calcRectTop(val: number) {
  if (isInsertTitle.value) {
    const dom = props.editor.view.domAtPos(val).node as HTMLElement

    const { top, left } = getDistanceToFirstScrollYParent(dom)
    rect.value.top = top
    rect.value.left = left
    rect.value.width = dom.clientWidth
    const nextSibling = dom.nextSibling! as HTMLElement
    titleDom.value = nextSibling
    const { left: leftTitle } = getDistanceToFirstScrollYParent(nextSibling)
    refreshIcon.value = { top: top + 8, left: leftTitle + dom.clientWidth + 9 }
  }
  else {
    const dom = document.querySelector('#article-title-input') as HTMLElement
    const { top, left } = getDistanceToFirstScrollYParent(dom)
    rect.value.top = top
    rect.value.width = dom.clientWidth
    rect.value.left = left
    titleDom.value = dom
    refreshIcon.value = { top: top - 12, left: left + dom.clientWidth + 9 }
  }
}

const endDom = ref()

const toolbarDom = ref()

const control = ref<undefined | AbortController>()

function calcRectHeight(val: number) {
  const dom = props.editor.view.domAtPos(val).node as HTMLElement
  endDom.value = dom
  const { top } = getDistanceToFirstScrollYParent(dom)
  rect.value.height = (top - rect.value.top) + dom.clientHeight
}

useResizeObserver(scrollContainer, () => {
  calcRectTop(boxStart.value)
  calcRectHeight(boxEnd.value)
})

const illegal_end = /\[[a-zA-Z0-9]+$/
async function generateArticle() {
  isLoading.value = true
  control.value = new AbortController()
  const res = await generateReview(props.data, control.value)
  isLoading.value = false

  if (props.data.use_trusted_website && res.data.value?.result.review) {
    const quotes = extraQuote(res.data.value?.result.review)
    collectRefContent([quotes])
  }

  if (res.data.value?.result?.review?.write_text) {
    const text = res.data.value.result.review.write_text
    content.value = text
    title.value = res.data.value.result.review.title
    title_list.value.push(res.data.value.result.review.title)
  }
  else if (res.data.value) {
    ElMessage({
      message: '算法返回了空内容',
      type: 'error',
    })
    $emits('back')
    props.editor.setEditable(true)
    return
  }
  else {
    $emits('back')
    props.editor.setEditable(true)
    return
  }

  const endPos = props.editor.state.doc.content.size
  props.editor.chain().focus().setTextSelection(endPos).run()
  await calcBox(false, res.data.value.result)
  await nextTick()
  toolbarDom.value?.scrollIntoView()
  if (scrollContainer.value)
    scrollContainer.value.scrollTop += 100
  if (currentUser.value?.extend_data?.generate_step_4) {
    await sleep(1000)
    scrollContainer.value?.scrollTo({
      top: rect.value.top - 20,
      behavior: 'smooth',
    })
  }
}

async function calcBox(refresh = false, res: sucRes) {
  isInserting.value = true

  contentRange.value.from = props.editor.state.selection.from
  let boxStart_ = 0
  if (!currentArticle.title.trim() && !currentArticle.plainText.trim()) {
    currentArticle.title = title.value
  }
  else {
    isInsertTitle.value = true
    props.editor.commands.insertContentAt(props.editor.state.selection.to, '<p></p>', {
      updateSelection: true,
    })
    boxStart_ = props.editor.state.selection.from
    props.editor.commands.insertContentAt(props.editor.state.selection.to + 1, `<h1>${title.value}</h1>`, {
      updateSelection: true,
    })
    props.editor.chain().focus().scrollIntoView().run()
  }

  let contetStart = props.editor.state.selection.to + 1
  if (!isInsertTitle.value)
    contetStart = props.editor.state.selection.from - 1

  let end = 0
  if (!refresh) {
    let content_ = splitText(content.value, 'continue')
    if (!content_.startsWith('<p>'))
      content_ = `<p>${content_}</p>`

    await typewriter(content_, async (text) => {
      if (illegal_end.test(text))
        text = text.slice(0, text.lastIndexOf('['))

      if (text.endsWith('['))
        text = text.slice(0, text.length - 1)

      text = transformQuoteSumData(text, res.review, res.materials)
      props.editor.commands.insertContentAt(end ? { from: contetStart, to: end } : contetStart, text, {
        updateSelection: true,
      })
      // props.editor.chain().focus().scrollIntoView().run()
      end = props.editor.state.selection.to
      const dom = props.editor.view.domAtPos(end).node as HTMLElement
      dom?.scrollIntoView?.()
    }, 10)
  }
  else {
    props.editor.commands.insertContentAt(contetStart, content.value, {
      updateSelection: true,
    })
    props.editor.chain().focus().scrollIntoView().run()
    end = props.editor.state.selection.to
  }

  props.editor.commands.insertContentAt({ from: end + 1, to: end + 1 }, '<p></p>', {
    updateSelection: true,
  })

  boxStart.value = boxStart_
  calcRectTop(boxStart.value)

  boxEnd.value = props.editor.state.selection.to
  calcRectHeight(boxEnd.value)
  contentRange.value.to = props.editor.state.selection.to

  visibleRect.value = true
  isInserting.value = false
}

onMounted(() => {
  generateArticle()
})

function clearState() {
  visibleRect.value = false
}

function apply() {
  clearState()
  props.editor.setEditable(true)
  $emits('apply')
  stats.track('text-generate', {
    action: 'apply',
  })
}

function before() {
  clearState()
  $emits('back')
  props.editor.setEditable(true)
  props.editor.commands.deleteRange({ from: contentRange.value.from, to: contentRange.value.to })
  if (!isInsertTitle.value)
    currentArticle.title = ''
}

const isLoadingTitle = ref(false)

function cancelReq() {
  control.value?.abort()
  ElMessage({
    message: '已取消生成',
    type: 'error',
  })
  isLoading.value = false
}
</script>

<template>
  <template v-if="isLoading || isLoadingTitle">
    <Teleport to="body">
      <div class="overlay">
        <div class="loading-container">
          <DocLoading :duration="isLoadingTitle ? 0 : loadingTime" :width="80" text-color="white" @cancle="cancelReq" />
        </div>
      </div>
    </Teleport>
  </template>
  <template v-else>
    <Teleport :to="scrollContainer">
      <div
        v-if="visibleRect"
        class="box absolute z-100" :style="{
          top: `${isInsertTitle ? rect.top : (rect.top - 20)}px`,
          left: `${rect.left - 30}px`,
          width: `${rect.width + 60}px`,
          height: `${isInsertTitle ? rect.height : (rect.height + 20)}px`,
        }"
        style="pointer-events: none;"
      />
      <div
        v-if="visibleRect"
        ref="toolbarDom"
        class="toolbar absolute z-10" :style="{
          width: `${rect.width + 60}px`,
          top: `${rect.top + rect.height + 17}px`,
          left: `${rect.left - 30}px`,
        }"
      >
        <div class="flex items-center">
          <el-button id="generate-step4-apply" type="primary" @click="apply">
            <span class="font-400">应用</span>
          </el-button>
          <el-button id="generate-step4-before">
            <span class=" text-[#19222E] font-400" @click="before">上一步</span>
          </el-button>
        </div>
        <div class="flex items-center">
          <DownUpIcon />
        </div>
      </div>
      <!-- <template v-if="visibleRect">
        <el-tooltip
          content="不满意标题？点此换一个"
        >
          <img
            id="generate-step4-refresh" class="absolute z-101 w-[14px] h-[14px] cursor-pointer"
            :style="{
              top: `${refreshIcon.top}px`,
              left: `${refreshIcon.left}px`,
            }"
            src="~/assets/images/generate/refresh.png"
            @click="refreshTitle"
          >
        </el-tooltip>
      </template> -->
      <div
        v-if="visibleRect"
        class="absolute z-10 h-[48px]" :style="{
          top: `${rect.top + rect.height + 17 + 48}px`,
          width: `${rect.width + 60}px`,
          left: `${rect.left - 30}px`,
        }"
      />
    </Teleport>
  </template>
</template>

<style lang="scss" scoped>
.loading-container {
    position: absolute;
    left: 50%;
    bottom: 74px;
    transform: translateX(-50%);
    color: var(--N2, #474E58);
    font-size: 18px;
    font-style: normal;
    font-weight: 600;
    line-height: normal;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.overlay {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  z-index: 1001;
}

.box {
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 19px;
    border-width: 2px;
    border-style: solid;
    border-image: linear-gradient(to right, rgba(164, 149, 255, 1), rgba(40, 62, 255, 1), rgba(219, 50, 222, 1), rgba(64, 68, 237, 1), rgba(54, 38, 153, 1)) 1 !important;
}

.box-refresh {
    border-radius: 3px;
    border: 1px solid #000;
    color: var(--N1, #19222E);
    font-size: 14px;
    font-style: normal;
    font-weight: 700;
    line-height: 22px; /* 157.143% */
    padding: 7px 10px;
    cursor: pointer;
    background-color: white;
    display: flex;
    align-items: center;
}

.toolbar {
  padding: 8px 16px;
  box-shadow: 0px 0px 12px rgba(0, 0, 0, 0.16);
  display: flex;
  justify-content: space-between;
  background-image: url('~/assets/images/generate/toolbar-bg.jpg');
  background-size: 100% 100%;
  background-repeat: no-repeat;
  border-radius: 10px;
}

.is-box-absolute {
  position: absolute;
    top: 17px;
    right: 19px;
}
.text1 {
  color: var(--N2, #474E58);
  font-size: 18px;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
}

.text3 {
  color: var(--grey1, #8B9096);
  text-align: center;
  font-size: 10px;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
}

.guide-box {
  background: linear-gradient(90deg, #4044ED -0.16%, #070DFF 75.42%);
  color: #FFF;
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  line-height: 22px;
  padding: 8px;
}

.guide-text-box {
  border-radius: 3px;
  border: 1px solid #D2D4D6;
}

.text2 {
  color: #0F14FD;
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  line-height: 22px;
}
</style>
