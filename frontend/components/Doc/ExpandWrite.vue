<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'
import { useWriting } from '~/composables/ai/useWriting'

const props = defineProps<{
  editor: Editor
}>()

const $emits = defineEmits<{
  (e: 'closed'): void
}>()

const type = computed(() => 'expand')

const {
  handleCopy,
  getTexts,
  getData,
  isloading,
  data,
  dataTranformed,
  currentSelection,
  currentText,
  currentAfterText,
  currentBeforeText,

  selectedTextIndex,
  isApply,
  isApplyIndexs,

  lastApplyFrom,
  lastApplyTo,
  lastApplyText,
  clearState,
  activeCurrentSelection,
  replaceText,
  trackForAppy,
  hintText,
  isValidInput,
  controller,
  isRefreh,
  isInit,
} = useWriting(type, props.editor)

async function refresh() {
  if (!isValidInput)
    return

  isRefreh.value = true
  activeCurrentSelection()
  selectedTextIndex.value = 0
  isApply.value = false
  isApplyIndexs.value = []
  await getData(true)
  handleSelection(0)
  isRefreh.value = false
}

function handleSelection(index: number) {
  if (!data.value[index])
    return
  selectedTextIndex.value = index
  activeCurrentSelection()
}

function handleApply(event: Event, index: number) {
  event.stopPropagation()

  const text = data.value[index]
  if (!text)
    return

  // tracking
  trackForAppy(index)

  const editor = props.editor
  let from, to, old_text
  if (lastApplyFrom.value === null || lastApplyTo.value === null) {
    from = currentSelection.from
    to = currentSelection.to
    old_text = currentText.value
  }
  else {
    from = lastApplyFrom.value
    to = lastApplyTo.value
    old_text = lastApplyText.value
  }

  if (old_text !== catchTextBetweenError(editor, from, to)) {
    ElMessage({
      message: '未找到匹配的文本，请重新选择',
      type: 'warning',
    })
    return
  }

  replaceText(index, from, to)
  isApplyIndexs.value.push(index)
  isApply.value = true
  ElMessage.success('已替换')
}

function closed() {
  clearState()
  $emits('closed')
}

const isVisibleFeedback = ref(false)
function handleUpDownChange(val: string) {
  if (val === 'dislike')
    isVisibleFeedback.value = true
}

function cancelReq() {
  controller.value?.abort()
  if (data.value.length === 0)
    closed()
}
async function init() {
  getTexts()
  await getData()
  handleSelection(0)
}
defineExpose({
  init,
  clear: (isSelectOrigin: boolean) => {
    clearState(isSelectOrigin)
  },
})
</script>

<template>
  <div class="sticky top-0 py-[16px] flex items-center justify-between bg-white z-10 h-[64px] shrink-0">
    <div class="flex items-center">
      <div class="i-ll-edit-continue-writing text-[16px] text-black-color" />
      <span class="text-black-color text-[14px] font-normal leading-[22px] ml-[6px]">扩写</span>
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
    <template v-if="(data.length === 0 && isloading) || isRefreh">
      <div class="w-full h-full flex flex-col items-center justify-center">
        <DocLoading :duration="40" :width="40" @cancle="cancelReq" />
      </div>
    </template>
    <template v-else-if="dataTranformed.length > 0 && !isloading">
      <div
        v-for="(item, index) in dataTranformed"
        :key="item"
        class="px-[24px] py-[16px] mb-[16px] rounded-[16px] box-border relative bg-[#F8F8F8]"
        :class="{
          'is-selected': (selectedTextIndex === index),
        }"
        @click="handleSelection(index)"
      >
        <div class="text-[14px] leading-[22px] text-black-color whitespace-pre-wrap">
          <span v-html="item" />
        </div>
        <div v-if="selectedTextIndex === index" class="flex items-center mt-[8px] justify-between">
          <div class="flex items-center">
            <div class="btn mr-[8px] flex items-center cursor-pointer" @click="handleApply($event, index)">
              <div class="i-ll-edit-apply text-[14px]" />
              <span class="text-[12px] ml-[4px]">替换原文</span>
            </div>

            <div class="btn flex items-center cursor-pointer" @click="handleCopy($event, index)">
              <div class="i-ll-edit-copy text-[14px]" />
              <span class="text-[12px] ml-[4px]">复制</span>
            </div>
          </div>
          <DocUpDownButton :type="type" :text="item" :selected_content="currentText" :context_above="currentBeforeText" :context_below="currentAfterText" @change="handleUpDownChange" />
        </div>
      </div>
    </template>
    <template v-else-if="data.length === 0 && !isloading">
      <p class="flex justify-center text-[14px] leading-[22px]">
        无请求结果，请刷新重试
      </p>
    </template>
  </template>
  <DocFeedbackDialog v-model="isVisibleFeedback" :type="type" :text="data[selectedTextIndex]" :selected_content="currentText" :context_above="currentBeforeText" :context_below="currentAfterText" />
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
</style>
