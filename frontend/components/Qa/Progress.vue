<script setup lang="ts">
import { QaMode, QaProgressState, useQaStore } from '~/store/qa'

const props = defineProps<{
  progress: string
}>()
const { progress } = toRefs(props)
const qaStore = useQaStore()
const { qaState } = storeToRefs(qaStore)

const progressValue = computed(() => {
  if (progress.value === QaProgressState.Analyze) {
    return {
      text1: '25%',
      value: 25,
      text2: '问题分析中',
      text3: 'AI正在努力分析您的意图...',
    }
  }
  else if (progress.value === QaProgressState.Search) {
    return {
      value: 50,
      text1: '50%',
      text2: qaState.value.mode === QaMode.WEB ? '全网搜索' : '文件搜索',
      text3: qaState.value.mode === QaMode.WEB ? '已启动搜索引擎，正在为您收集最权威的参考资料' : '正在检索您上传的资料内容',
    }
  }
  else if (progress.value === QaProgressState.Organize) {
    return {
      value: 75,
      text1: '75%',
      text2: '整理答案',
      text3: '答案准备就绪，正在进行润色以保证完美呈现',
    }
  }
  else if (progress.value === QaProgressState.Complete) {
    return {
      value: 100,
      text1: '100%',
      text2: qaState.value.mode === QaMode.WEB ? '完成' : '整理完毕',
      text3: qaState.value.mode === QaMode.WEB ? '感谢您的等待，答案马上揭晓' : '',
    }
  }
  return null
})

const isVisibleProgress = computed(() => {
  if (progress.value === QaProgressState.Finish)
    return false
  if (progress.value === QaProgressState.Supplement)
    return false
  if (progress.value === QaProgressState.TextEnd)
    return false
  return true
})

const isVisibleSkeleton = computed(() => {
  if (progress.value === QaProgressState.Finish)
    return false
  if (progress.value === QaProgressState.Supplement)
    return false
  if (progress.value === QaProgressState.Complete)
    return false
  if (progress.value === QaProgressState.TextEnd)
    return false
  return true
})

const isVisible = computed(() => {
  if (progress.value === QaProgressState.Finish)
    return false
  if (progress.value === QaProgressState.Supplement)
    return false
  if (progress.value === QaProgressState.TextEnd)
    return false
  if (progress.value === QaProgressState.Complete)
    return false
  return true
})
</script>

<template>
  <div v-if="isVisible" class="w-[660px] mb-[32px]">
    <template v-if="isVisibleProgress">
      <div class="flex items-center mb-[8px]">
        <span class="text-[14px] font-800 leading-normal text-normal-color">{{ progressValue?.text1 }}</span>
        <div class="mx-[8px] w-[1px] h-[12px] opacity-20 bg-[#4044ED]" />
        <span class="text-[14px] font-500 leading-normal mr-[8px] text-[rgba(0,0,0,0.9)]]">{{ progressValue?.text2 }}</span>
        <span class="text-[12px] font-normal leading-normal text-[#9E9E9E]">{{ progressValue?.text3 }}</span>
      </div>
      <MProgress
        v-if="progressValue"
        :percentage="progressValue?.value"
        :show-text="false"
      />
    </template>
    <template v-if="isVisibleSkeleton">
      <el-skeleton style="width: 660px; margin-top: 32px;" :loading="true" animated>
        <el-skeleton-item style="width: 660px; height: 24px" />
        <el-skeleton-item style="width: 660px; height: 24px; margin-top: 16px; " />
        <el-skeleton-item style="width: 460px; height: 24px; margin-top: 16px; " />
      </el-skeleton>
    </template>
  </div>
</template>
