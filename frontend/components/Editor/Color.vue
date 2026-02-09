<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'

const props = defineProps<{
  editor: Editor | undefined
}>()

const recentColorStr = useLocalStorage('recent-color', '')
const recentColor = computed({
  get() {
    if (recentColorStr.value)
      return JSON.parse(recentColorStr.value)

    return []
  },
  set(val) {
    recentColorStr.value = JSON.stringify(val)
  },
})
const recentColorFilled = computed(() => {
  if (recentColor.value.length < 6)
    return recentColor.value.concat(Array(6 - recentColor.value.length).fill(''))

  return recentColor.value
})

const standardColor = ['#B12418', '#EB3323', '#F0AF41', '#ECCA62', '#89B136', '#569B30', '#43959A',
  '#3479F6', '#203EBC', '#B5337D', '#4C27A4', '#06215C']

const currentColor = computed(() => {
  return props.editor?.getAttributes('textStyle').color || ''
})
const inputColor = ref()
function handleInputColor(e: Event) {
  const target = e.target as HTMLInputElement
  handleColor(target.value)
}

function handleMoreColor() {
  inputColor.value?.click()
}

function handleColor(color: string) {
  props.editor?.chain().focus().setColor(color).run()
  let colors = [...recentColor.value]
  colors = colors.filter(c => c !== color)
  colors.unshift(color)
  colors = colors.slice(0, 6)
  recentColor.value = colors
}

function setDefaultColor() {
  props.editor?.chain().focus().unsetColor().run()
}
</script>

<template>
  <el-popover width="196" trigger="click">
    <div class="default-color" @click="setDefaultColor">
      <span>默认</span>
    </div>
    <div class="grid grid-cols-6 gap-[4px] w-full my-[8px]">
      <div
        v-for="color in standardColor"
        :key="color"
        :style="{
          backgroundColor: color,
          width: '24px',
          height: '24px',
          borderRadius: '50%',
          cursor: 'pointer',
        }"
        @click="handleColor(color)"
      />
    </div>
    <div class="mt=[4px] normal-text">
      最近使用
    </div>
    <div class="grid grid-cols-6 gap-[4px] w-full mt-[8px] mb-[4px]">
      <div
        v-for="color in recentColorFilled"
        :key="color"
        :style="{
          backgroundColor: color || 'white',
          border: color ? 'none' : '1px solid #D9D9D9',
          boxSizing: 'border-box',
          width: '24px',
          height: '24px',
          borderRadius: '50%',
          cursor: 'pointer',
        }"
        @click="handleColor(color)"
      />
    </div>
    <div class="divider" />
    <div class="flex items-center justify-between hover:bg-[#F5F5F5] cursor-pointer p-[4px]" @click="handleMoreColor">
      <span>更多颜色</span>
      <div class="i-ll-triangle text-[6px] text-gray-lighter-color rotate-90" />
    </div>
    <div class="relative">
      <input
        ref="inputColor"
        type="color"
        :value="currentColor"
        class="color-picker"
        @input="handleInputColor"
      >
    </div>
    <template #reference>
      <button
        class="cursor-pointer flex items-center"
        :style="{
          color: currentColor || 'rgba(0,0,0,0.45)',
        }"
      >
        <div class="i-ll-edit-color text-[20px]" />
        <div class="ml-[4px] i-ll-triangle text-[6px] -rotate-180" />
      </button>
    </template>
  </el-popover>
</template>

<style lang="scss" scoped>
.default-color {
    width: 100%;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 13px;
    border: 1px solid  #D9D9D9;
    cursor: pointer;

    span {
        color: rgba(0, 0, 0, 0.85);
        text-align: center;
        font-family: Alibaba PuHuiTi 2.0;
        font-size: 14px;
        font-style: normal;
        font-weight: 400;
        line-height: 22px; /* 157.143% */
    }
}

.normal-text {
    color: rgba(0, 0, 0, 0.36);
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px; /* 157.143% */
}

.divider {
    width: 100%;
    height: 1px;
    background-color: rgba(0, 0, 0, 0.06);
    margin: 8px 0;
}

.color-picker {
  visibility: hidden;
  width: 1px;
  height: 1px;
  position: absolute;
  left: 100%;
  top: -30px;
}
</style>
