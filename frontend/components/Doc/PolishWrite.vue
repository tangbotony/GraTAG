<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'
import { diffChars } from 'diff'
import { useWriting } from '~/composables/ai/useWriting'

const props = defineProps<{
  editor: Editor
}>()

const $emits = defineEmits<{
  (e: 'closed'): void
}>()

const style = inject<Ref<string>>('currentAIStyle')

const type = computed(() => 'polish')

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
} = useWriting(type, props.editor, style)

const polishkinds = [
  { type: 'xinhua_style', title: '新华体润色' },
]

const currentPolishType = ref('xinhua_style')

const checkDiff = ref(true)

watch(currentPolishType, (val) => {
  if (val)
    refresh()
})

const diffData = computed(() => {
  return data.value.map((item) => {
    const diffs = diffChars(currentText.value, item).map(i => ({
      type: i.added ? 'added' : (i.removed ? 'removed' : 'normal'),
      text: i.value,
    }))
    return diffs
  })
})

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
      message: '未找到匹配的文本',
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
  <div class="sticky top-0 z-10 py-[16px] flex items-center justify-between bg-white h-[64px] shrink-0">
    <div class="flex items-center">
      <div class="i-ll-edit-continue-writing text-[16px] text-black-color" />
      <span class="text-black-color text-[14px] font-normal leading-[22px] ml-[6px]">润色</span>
    </div>
    <div class="flex items-center">
      <el-switch v-model="checkDiff" inline-prompt inactive-text="对比" active-text="对比" />

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
  <div class=" sticky top-[64px] z-10 flex items-center pb-[16px] bg-white">
    <div
      v-for="kind in polishkinds"
      :key="kind.type"
      class="polish-tag mr-[8px] cursor-pointer"
      :class="{
        'is-active': (currentPolishType === kind.type),
      }"
      @click="currentPolishType = kind.type"
    >
      <span>{{ kind.title }}</span>
    </div>
  </div>
  <template v-if="!isValidInput">
    <template v-if="isInit">
      <div class="w-full h-full  flex flex-col items-center justify-center">
        <img class="w-[140px] h-[140px]" src="~/assets/images/edit-empty.png">
        <span class="text-[15px] text-[rgba(0,0,0,0.78)] mt-[32px] leading-[1.5] inline-block max-w-[300px]">{{ hintText }}</span>
      </div>
    </template>
  </template>
  <template v-else>
    <template v-if="(data.length === 0 && isloading) || isRefreh">
      <div class="w-full h-full flex flex-col items-center justify-center">
        <DocLoading :duration="20" :width="40" @cancle="cancelReq" />
      </div>
    </template>
    <template v-else-if="diffData.length > 0 && !isloading">
      <div
        v-for="(item, index) in diffData"
        :key="index"
        class="px-[24px] py-[16px] mb-[16px] rounded-[16px] box-border relative bg-[#F8F8F8]"
        :class="{
          'is-selected': (selectedTextIndex === index),
        }"
        @click="handleSelection(index)"
      >
        <div class="text-[14px] leading-[22px] text-black-color whitespace-pre-line">
          <template v-if="checkDiff">
            <span
              v-for="(diff, diffIndex) in item"
              :key="diffIndex"
              :class="{
                'text-deepblue-color': diff.type === 'added',
                'text-deleted': diff.type === 'removed',
              }"
            >{{ diff.text }}</span>
          </template>
          <template v-else>
            <span
              v-for="(text, _) in data[index]"
              :key="_"
            >{{ text }}</span>
          </template>
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
          <DocUpDownButton :type="type" :text="data[index]" :selected_content="currentText" :context_above="currentBeforeText" :context_below="currentAfterText" :polish_type="currentPolishType" @change="handleUpDownChange" />
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

.polish-tag {
    display: flex;
    padding: 0px 7px;
    justify-content: center;
    align-items: center;
    border-radius: 12px;
    border-radius: 12px;
    border: 1px solid  #D9D9D9;
    background:  #FFF;

    span {
        color: rgba(0,0,0,0.85);
        text-align: center;
        font-size: 14px;
        font-style: normal;
        font-weight: 400;
        line-height: 22px; /* 157.143% */
    }

    &.is-active {
        border: 1px solid #4044ED;
        background: #E5E6FF;

        span {
            color: #4044ED;
        }
    }
}

.text-deleted {
  color: red;
  text-decoration: line-through;
}
</style>
