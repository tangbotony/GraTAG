<script lang="ts" setup>
import type { Editor } from '@tiptap/vue-3'

const props = defineProps<{
  editor: Editor | undefined
}>()

const fontSizeMap: Record<string, string> = {
  default: '默认字号',
  12: '12',
  14: '14',
  15: '16',
  18: '18',
  20: '20',
  22: '22',
  24: '24',
  25: '25',
  26: '26',
  28: '28',
  30: '30',
  35: '35',
  36: '36',
  40: '40',
  42: '42',
  48: '48',
  72: '72',
}
const fontSizeSet = ['default', '12', '14', '15', '18', '20', '22', '24', '25', '26', '28', '30', '35', '36', '40', '42', '48', '72']

const currentFontSize = computed(() => {
  return props.editor?.getAttributes('textStyle').fontSize || 'default'
})

function handleFontFamily(val: string) {
  if (val === 'default')
    props.editor?.commands.unsetFontSize()
  else
    props.editor?.commands.setFontSize(Number(val))
}
</script>

<template>
  <el-dropdown max-height="200" trigger="click" @command="handleFontFamily">
    <button
      class="cursor-pointer flex items-center"
    >
      <span class="inline-block w-[54px] text-[11px]">{{ fontSizeMap[currentFontSize] }}</span>
      <div class="ml-[4px] i-ll-triangle text-[6px] -rotate-180 text-gray-lighter-color" />
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="item in fontSizeSet"
          :key="item"
          :command="item"
        >
          <div
            class="w-[116px]"
            :class="{
              'text-normal-color': currentFontSize === item,
            }"
          >
            {{ fontSizeMap[item] }}
          </div>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style lang="scss" scoped>
</style>
