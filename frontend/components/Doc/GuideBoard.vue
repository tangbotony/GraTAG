<script setup lang="ts">
import { WRITE_KIND } from '~/consts/editor'
import stats from '~/lib/stats'

const $emits = defineEmits<{
  (e: 'change', value: string): void
}>()

const functions = ref([
  {
    key: WRITE_KIND.Generate,
    icon: 'i-ll-edit-generate',
    title: 'AI全文写作',
    description: '利用AI技术自动生成完整文章',
  },
  {
    key: WRITE_KIND.Continue,
    icon: 'i-ll-edit-continue-writing',
    title: '通用续写',
    description: '基于文本接续自动生成后续内容',
  },
  {
    key: WRITE_KIND.ContinuePro,
    icon: 'i-ll-edit-continue-writing',
    title: '专业续写',
    description: '支持指定领域与风格的内容续写',
  },
  {
    key: WRITE_KIND.Polish,
    icon: 'i-ll-edit-polish-writing',
    title: '润色',
    description: '自动优化文本语言风格和格式',
  },
  {
    key: WRITE_KIND.Expand,
    icon: 'i-ll-edit-expand-writing',
    title: '扩写',
    description: '自动增强和丰富文本细节',
  },
  {
    key: WRITE_KIND.Title,
    icon: 'i-ll-edit-h',
    title: '标题生成',
    description: '快速生成吸引力强的文章标题',
  },
])

function handleClick(key: string) {
  $emits('change', key)
  stats.track(`text-${key}`, { action: 'click' })
}
</script>

<template>
  <div class="board-container flex justify-center">
    <div class="flex flex-col w-[1068px] items-start overflow-visible">
      <p class="text-[20px] font-medium leading-[normal] tracking-[.3px]">
        使用AI开始写作
      </p>
      <div class="flex flex-wrap w-[1068px] gap-[16px] mt-[28px]">
        <div
          v-for="item in functions"
          :key="item.key"
          class="item"
          @click="handleClick(item.key)"
        >
          <div :class="item.icon" class="text-[28px] text-normal-color" />
          <div class="ml-[12px]">
            <div class="text-[16px] text-black-color font-400 leading-[normal] mb-[4px]">
              {{ item.title }}
            </div>
            <div class="text-[12px] text-[rgba(0,0,0,0.65)] font-400 leading-[normal]">
              {{ item.description }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.board-container {
    background: linear-gradient(180deg, #fff, #E5E6FF 100%);
    width: 100%;
    height: 100%;
}

.item {
    width: 260px;
    height: 80px;
    flex-shrink: 0;
    border-radius: 16px;
    border: 1px solid #F5F5F5;
    background: #FFF;
    box-shadow: 0px 0px 16px 0px rgba(0, 0, 0, 0.10);
    box-sizing: border-box;
    padding: 19px 20px 18px 20px;
    display: flex;
    align-items: center;
    cursor: pointer;
}
</style>
