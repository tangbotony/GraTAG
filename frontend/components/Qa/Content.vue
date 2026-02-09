<script setup lang="ts">
import markdownit from 'markdown-it'
import copyToClipboard from 'copy-to-clipboard'
import type { QaCollectionState } from '~/store/qa'
import { QaAnswerType, QaMode, QaProgressState, useQaStore } from '~/store/qa'
import ParsedHtml from '~/components/ParsedHtml'

const props = defineProps<{
  content: string
  progress: string
  id: string
  collection: QaCollectionState
}>()

const $emits = defineEmits<{
  (e: 'sub'): void
  (e: 'gen'): void
}>()

const md = markdownit()

const { collection } = toRefs(props)
const currPair = computed(() => {
  return collection.value.pairs.find(i => i._id === collection.value.curPairId)
})

const qaStore = useQaStore()
const illegal_end = /\[[a-zA-Z0-9]+$/
const illegalCode = /\[[a-zA-Z0-9]+\]/g
const html = computed(() => {
  const value = props.content
  let html_ = value.replaceAll(/<xinyu[^>]*\/>/g, '')
  if (illegal_end.test(html_))
    html_ = html_.slice(0, html_.lastIndexOf('['))

  if (html_.endsWith('['))
    html_ = html_.slice(0, html_.length - 1)

  html_ = addSpaceToMarkdown(html_)
  html_ = md.render(html_)

  const pair = props.collection.pairs.find(i => i._id === props.collection.curPairId)
  if (pair && pair.qa_info) {
    const refs = pair.reference || []

    if (refs.length > 0)
      html_ = qaStore.pageHtml2Ref(html_, refs, pair, props.collection)
  }

  html_ = html_.replace(illegalCode, '')
  return html_
})

// watch(html, () => {
//   qaStore.scrollerContainer?.scroll({
//     top: qaStore.scrollerContainer.scrollHeight + qaStore.scrollerContainer.clientHeight,
//     behavior: 'smooth',
//   })
// })

function copy() {
  if (!props.content)
    return

  const content = md2Text(props.content)
  copyToClipboard(content, {
    format: 'text/html',
    onCopy(data: any) {
      data.setData('text/plain', content)
    },
  })

  ElMessage({
    message: '复制成功',
    type: 'success',
  })
}

function reAsk() {
  qaStore.reAsk(props.id, QaAnswerType.ReGenerate)
}

function sub() {
  $emits('sub')
}

const currPairIndex = computed(() => {
  return collection.value.pairsIds.findIndex(i => i === collection.value.curPairId)
})

function beforePair() {
  if (currPairIndex.value === 0)
    return

  collection.value.curPairId = collection.value.pairsIds[currPairIndex.value - 1]
}
async function afterPair() {
  if (currPairIndex.value === collection.value.pairsIds.length - 1)
    return

  collection.value.curPairId = collection.value.pairsIds[currPairIndex.value + 1]
  const pair = collection.value.pairs.find(i => i._id === collection.value.curPairId)
  if (!pair)
    qaStore.getPair(collection.value.curPairId, collection.value.id)
}

function genNews() {
  $emits('gen')
}

const contentRef = ref()

useEventListener(contentRef, 'click', (event: MouseEvent) => {
  const target = event.target as HTMLImageElement
  if (target.tagName === 'IMG') {
    event.preventDefault()
    const pair = collection.value.pairs.find(i => i._id === collection.value.curPairId)
    const img = pair?.images?.find(i => i.url === target.src)
    if (img)
      window.open(img.origin_doc_url, '_blank')
  }
})
</script>

<template>
  <article ref="contentRef" class="html-container w-[660px] mt-[24px]">
    <div
      v-if="(currPair?.unsupported === 1) && html && html.length > 0"
      class="flex items-center mb-[8px]"
    >
      <div class="i-ll-warning text-[#E37318] text-[14px] mr-[4px]" />
      <div class="text-[rgba(0,0,0,0.6)] text-[12px] font-normal leading-[22px]">
        非常抱歉，咱现在还不支持生成图表呢，算法工程师正在加急开发中~
      </div>
    </div>
    <!-- <p v-html="html" /> -->
    <ParsedHtml :content="html" />
  </article>
  <template v-if="props.progress === QaProgressState.Finish">
    <div class="flex items-center mt-[16px] mb-[32px] w-full justify-between">
      <div class="flex items-center">
        <DownUpIcon />
      </div>
      <div class="flex items-center">
        <div v-if="collection.pairsIds.length > 1" class="flex items-center mr-[8px]">
          <div
            class="i-ll-arrow-left text-[14px] origin-center cursor-pointer mr-[2px]" :class="{
              'cursor-not-allowed': currPairIndex === 0,
              'text-[rgba(0,0,0,0.4)]': currPairIndex === 0,
            }"
            @click="beforePair()"
          />
          <div class="text-[12px] text-[#262626]">
            <span>{{ currPairIndex + 1 }}</span>
            <span> / {{ collection.pairsIds.length }}</span>
          </div>
          <div
            class="i-ll-arrow-left rotate-180 text-[14px] cursor-pointer ml-[2px]"
            :class="{
              'cursor-not-allowed': (currPairIndex + 1) === collection.pairsIds.length,
              'text-[rgba(0,0,0,0.4)]': (currPairIndex + 1) === collection.pairsIds.length,
            }"
            @click="afterPair()"
          />
        </div>
        <div class="box mr-[8px]" @click="copy">
          <div class="item i-ll-copy-2 text-[14px] text-[rgba(0,0,0,0.6)]" />
        </div>
        <div class="box mr-[8px]" @click="reAsk">
          <span class="item text-[12px] text-[rgba(0,0,0,0.6)] font-normal leading-[20px]">
            重新回答
          </span>
        </div>
        <template v-if="currPair?.search_mode !== QaMode.DOC">
          <div class="box mr-[8px]" @click="sub">
            <span
              class=" item text-[12px]  leading-[20px]" :class="{
                'text-[#4044ED]': !collection.is_subscribed,
                'text-[rgba(0,0,0,0.6)]': collection.is_subscribed,
              }"
            >
              {{ collection.is_subscribed ? '取消订阅' : '订阅最新进展' }}
            </span>
          </div>
          <div class="rounded-[12px] flex items-center justify-center py-[2px] px-[10px] bg-[#4044ED] cursor-pointer" @click="genNews">
            <span class="text-[12px] leading-[20px] text-white">一键生成文章</span>
          </div>
        </template>
      </div>
    </div>
  </template>
</template>

<style lang="scss" scoped>
.box {
    cursor: pointer;
    padding: 3px 10px;
    display: flex;
    justify-content: center;
    align-items: center;
    background: #FFFFFF;
    border: 1px solid #EEEEEE;
    border-radius: 12px;
    height: 26px;
    &:hover {
      .item {
        color: #4044ED !important;
      }
      border-color: #4044ED;
    }
}
</style>

<style lang="scss">
.qa-ref {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px !important;
  height: 16px !important;
  font-size: 12px;
  line-height: 14px;
  border-radius: 50%;
  background-color: #EEE;
  color: rgba(0, 0, 0, 0.4);
  cursor: pointer;
  margin-left: 2px;
  transition: 0s;
  vertical-align: super;

  &:hover {
    background-color: #4044ED !important;
    color: white !important;
  }
}

.mutil-abs, .abs {
  .qa-ref {
    vertical-align: top;
  }
}
</style>
