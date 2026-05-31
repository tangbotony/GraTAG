<script lang="ts" setup>
import type { Editor } from '@tiptap/vue-3'

const props = defineProps<{
  editor: Editor | undefined
}>()

const fontMap: Record<string, string> = {
  'default': '默认字体',
  'source-han-serif': '思源宋体',
  'source-han-sans': '思源黑体',
  'fzktjt': '方正楷体',
  'fzfsjt': '方正仿宋',
}
const fontFamilies = Object.keys(fontMap)

const currentFontFamily = computed(() => {
  return props.editor?.getAttributes('textStyle').fontFamily || 'default'
})
const fontDisplay = computed(() => {
  return fontMap[props.editor?.getAttributes('textStyle').fontFamily] || '默认字体'
})
function handleFontFamily(val: string) {
  if (val === 'default')
    props.editor?.commands.unsetFontFamily()
  else
    props.editor?.commands.setFontFamily(`${val}`)
}
</script>

<template>
  <el-dropdown trigger="click" @command="handleFontFamily">
    <button
      class="cursor-pointer flex items-center"
    >
      <span class="text-[11px]">{{ fontDisplay }}</span>
      <div class="ml-[4px] i-ll-triangle text-[6px] -rotate-180 text-gray-lighter-color" />
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="item in fontFamilies"
          :key="item"
          :command="item"
        >
          <div
            class="w-[116px]"
            :class="{
              'text-normal-color': currentFontFamily === item,
            }"
          >
            {{ fontMap[item] }}
          </div>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style lang="scss" scoped>
</style>
