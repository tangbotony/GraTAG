<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'
import type { FormDataType } from './ProFrom.vue'
import { useWriting } from '~/composables/ai/useWriting'
import stats from '~/lib/stats'
import { WRITE_KIND } from '~/consts/editor'

const props = defineProps<{
  editor: Editor
  type: string
}>()

const $emits = defineEmits<{
  (e: 'closed'): void
  (e: 'change', value: string): void
}>()

const type = computed(() => props.type)

const {
  handleCopy,
  getTexts,
  getData,
  isloading,
  data,
  currentSelection,
  currentText,
  currentBeforeText,
  currentAfterText,
  currentArticle,

  selectedTextIndex,
  isApply,

  lastApplyFrom,
  lastApplyTo,
  lastApplyText,
  clearState,
  activeCurrentSelection,
  replaceText,

  proContinueData,
  dataTranformed,
  dataQuote,
  trackForAppy,
  isValidInput,
  hintText,
  controller,
  isRefreh,
  isInit,
} = useWriting(type, props.editor)

async function loadMore() {
  activeCurrentSelection()
  const lastIndex = data.value.length - 1
  await getData()
  if (lastIndex === data.value.length - 1)
    return
  isApply.value = false
  handleSelection(lastIndex + 1)
}

async function refresh() {
  if (!isValidInput)
    return

  isRefreh.value = true
  activeCurrentSelection()
  isApply.value = false
  await getData(true)
  handleSelection(0)
  isRefreh.value = false
}

function handleSelection(index: number) {
  if (!data.value[index])
    return

  const text = data.value[index]
  selectedTextIndex.value = index
  const editor = props.editor
  let from, to
  if (lastApplyFrom.value === null || lastApplyTo.value === null) {
    from = currentSelection.to
    to = currentSelection.to + text.length
  }
  else {
    from = lastApplyFrom.value
    to = lastApplyTo.value
    if (lastApplyText.value !== catchTextBetweenError(editor, from, to)) {
      ElMessage({
        message: '未找到匹配的文本，请重新选择',
        type: 'warning',
      })
      return
    }
  }
  quoteState.currentQuote = null

  if (lastApplyTo.value)
    replaceText(index, from, to)

  else
    replaceText(index, from)
}

function handleApply(event: Event, index: number) {
  event.stopPropagation()

  // tracking
  trackForAppy(index)

  isApply.value = true
  ElMessage.success('已应用')
}

function closed() {
  clearState()
  $emits('closed')
}

const step = ref(1)

function handleProFormSubmit(data: FormDataType) {
  proContinueData.pro_setting_language_type = data.style
  proContinueData.pro_setting_special_request = data.demand || ''
  proContinueData.pro_setting_continue_direction = data.direction.reduce((obj: Record<string, string>, cur) => {
    obj[cur.type] = cur.value
    return obj
  }, {})

  const fields = ['aspect', 'keywords', 'direction', 'orientation']
  fields.forEach((key: string) => {
    if (!proContinueData.pro_setting_continue_direction[key])
      proContinueData.pro_setting_continue_direction[key] = ''
  })
  proContinueData.pro_setting_length = data.length

  refresh()
}

const isVisibleFeedback = ref(false)
function handleUpDownChange(val: string) {
  if (val === 'dislike')
    isVisibleFeedback.value = true
}

function handleSwitch(type: string) {
  if (props.type === type)
    return

  $emits('change', type)
  stats.track(`text-${type}`, { action: 'click' })
}

function cancelReq() {
  controller.value?.abort()
  if (data.value.length === 0)
    closed()
}

watch(step, (val, oldVal) => {
  if (val === 1 && oldVal === 2)
    controller.value?.abort()
})

const duration = computed(() => {
  if (type.value === WRITE_KIND.Continue && !currentArticle.isQuote)
    return 25

  else if (type.value === WRITE_KIND.ContinuePro && !currentArticle.isQuote)
    return 25

  else if (type.value === WRITE_KIND.Continue && currentArticle.isQuote)
    return 80

  else if (type.value === WRITE_KIND.ContinuePro && currentArticle.isQuote)
    return 80
})

async function init() {
  getTexts()

  if (type.value === 'continue_profession')
    return
  await getData()
  handleSelection(0)
}

defineExpose({
  init,
  clear: (isSelectOrigin: boolean) => {
    clearState(isSelectOrigin)
    step.value = 1
  },
})
</script>

<template>
  <div class="sticky top-0 py-[16px] flex items-center justify-between bg-white z-10 h-[64px] shrink-0">
    <div class="flex items-center">
      <div class="i-ll-edit-continue-writing text-[16px] text-black-color" />
      <span class="text-black-color text-[14px] font-normal leading-[22px] ml-[6px]">续写</span>
      <template v-if="WRITE_KIND.Continue === type">
        <el-switch v-model="currentArticle.isQuote" class="ml-[8px]" :width="42" size="small" inline-prompt active-text="引证" inactive-text="引证" />
      </template>
      <template v-else-if="WRITE_KIND.ContinuePro === type">
        <el-switch v-model="currentArticle.isQuote" class="ml-[8px]" :width="42" size="small" inline-prompt active-text="引证" inactive-text="引证" />
      </template>
    </div>
    <div class="radio-box">
      <div
        class="radio-item" :class="{
          'is-active': type === 'continue',
        }"
        @click="handleSwitch('continue')"
      >
        通用续写
      </div>
      <div
        class="radio-item" :class="{
          'is-active': type === 'continue_profession',
        }"
        @click="handleSwitch('continue_profession')"
      >
        专业续写
      </div>
    </div>
    <div class="flex items-center">
      <el-tooltip
        content="更新"
      >
        <div class="btn" @click="refresh">
          <div class="i-ll-edit-refresh text-[20px]" />
        </div>
      </el-tooltip>
      <el-tooltip
        content="关闭"
      >
        <div class="btn" @click="closed">
          <div class="i-ll-close text-[20px]" />
        </div>
      </el-tooltip>
    </div>
  </div>
  <template v-if="!isValidInput">
    <template v-if="isInit">
      <div class="w-full h-full flex flex-col items-center justify-center">
        <img class="w-[140px] h-[140px]" src="~/assets/images/edit-empty.png">
        <span class="text-[15px] leading-[1.5] text-[rgba(0,0,0,0.78)] mt-[32px] inline-block max-w-[300px]">{{ hintText }}</span>
      </div>
    </template>
  </template>
  <template v-else>
    <template v-if="type === 'continue_profession'">
      <DocContinueProFrom v-model:step="step" @submit="handleProFormSubmit" />
    </template>
    <template v-if="!(type === 'continue_profession' && step === 1)">
      <template v-if="(data.length === 0 && isloading) || isRefreh">
        <div class="w-full h-full flex flex-col items-center justify-center">
          <DocLoading :duration="duration" :width="40" @cancle="cancelReq" />
        </div>
      </template>
      <template v-else-if="data.length === 0 && !isloading">
        <p class="flex justify-center text-[14px] leading-[22px]">
          您选中的内容我不太懂呢，可以重新选择下嘛～
        </p>
      </template>
      <template v-else-if="data.length > 0">
        <div
          v-for="(item, index) in dataTranformed"
          :key="item"
          class="py-[16px] rounded-[16px] box-border relative bg-[#F8F8F8] mb-[16px]"
          :class="{
            'is-selected': (selectedTextIndex === index),
          }"
          @click="handleSelection(index)"
        >
          <div class="px-[24px] text-[14px] leading-[22px] text-black-color whitespace-pre-wrap continue-container">
            <span>{{ currentText }}</span>
            <span class="text-deepblue-color" v-html="item" />
          </div>
          <div v-if="selectedTextIndex === index" class="px-[24px] flex items-center mt-[8px] justify-between">
            <div class="flex items-center">
              <div class="btn mr-[8px] flex items-center cursor-pointer" @click="handleApply($event, index)">
                <div class="i-ll-edit-apply text-[14px]" />
                <span class="text-[12px] ml-[4px]">应用</span>
              </div>

              <div class="btn flex items-center cursor-pointer" @click="handleCopy($event, index)">
                <div class="i-ll-edit-copy text-[14px]" />
                <span class="text-[12px] ml-[4px]">复制</span>
              </div>
            </div>
            <DocUpDownButton :type="type" :pro-continue-data="proContinueData" :text="data[index]" :selected_content="currentText" :context_above="currentBeforeText" :context_below="currentAfterText" @change="handleUpDownChange" />
          </div>
        </div>
        <div class="flex items-center justify-center mt-[16px]" @click="loadMore">
          <div class="btn-loadmore">
            {{ isloading ? '加载中...' : '加载更多' }}
          </div>
        </div>
      </template>
    </template>
  </template>
  <DocFeedbackDialog v-model="isVisibleFeedback" :type="type" :text="data[selectedTextIndex]" :pro-continue-data="proContinueData" :selected_content="currentText" :context_above="currentBeforeText" :context_below="currentAfterText" />
</template>

<style lang="scss" scoped>
.btn {
    padding: 0 8px;
    border-radius: 4px;
    cursor: pointer;
    color: rgba(0, 0, 0, 0.36);
    &:hover {
        color: var(--c-text-black);
        background: #F1F1F1;
    }
}

.is-selected:before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 16px;
  border: 2px solid #4044ED;
  pointer-events: none;
}

.btn-loadmore {
  display: flex;
  padding: 4px 15px;
  justify-content: center;
  align-items: center;
  border-radius: 20px;
  border: 1px solid #D9D9D9;
  cursor: pointer;

  color: var(--c-text-black);
  font-size: 14px;
  font-style: normal;
  font-weight: 400;
  line-height: 22px;
  text-align: center;
}

.radio-box {
  border-radius: 16px;
  display: flex;

  .radio-item {
    flex: 1;
    background-color: white;
    border: 1px solid  #D9D9D9;
    box-sizing: border-box;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px;
    color: black;
    padding: 5px 16px;
    cursor: pointer;

    &:first-child {
      border-radius: 16px 0px 0px 16px;
    }

    &:last-child {
      border-radius: 0px 16px 16px 0px;
    }

    &.is-active {
      border: 1px solid #4044ED;
      background: #E5E6FF;
      color: #4044ED;
    }
  }
}

.link {
  font-size: 12px;
  color: #4044ED;
  font-style: normal;
  font-weight: 400;
  line-height: 22px;
  background-color: #E5E6FF;
  padding: 0 6px;
}
</style>
