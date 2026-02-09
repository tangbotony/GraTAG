<script lang="ts" setup>
import type { Editor } from '@tiptap/vue-3'

const props = defineProps<{
  editor: Editor | undefined
}>()

const LeadingMap: Record<string, string> = {
  default: '默认',
  1: '1',
  1.15: '1.15',
  1.5: '1.5',
  2: '2',
  2.5: '2.5',
  3: '3',
}
const LeadingSet = ['default', '1', '1.15', '1.5', '2', '2.5', '3']

const currentLeading = computed(() => {
  if (props.editor?.isActive('heading'))
    return props.editor?.getAttributes('heading').lineHeight || 'default'

  else
    return props.editor?.getAttributes('paragraph').lineHeight || 'default'
})

function handleLeading(val: string) {
  if (val === 'default')
    props.editor?.commands.unsetleading()
  else
    props.editor?.commands.setLeading(val)
}
</script>

<template>
  <el-dropdown max-height="200" trigger="click" @command="handleLeading">
    <button
      class="cursor-pointer flex items-center"
      :class="{
        'text-[rgba(0,0,0,0.87)]': currentLeading !== 'default',
        'text-gray-lighter-color': currentLeading === 'default',
      }"
    >
      <div class="i-ll-line-height text-[20px]" />
      <div class="ml-[4px] i-ll-triangle text-[6px] -rotate-180" />
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="item in LeadingSet"
          :key="item"
          :command="item"
        >
          <div
            class="w-[116px]"
            :class="{
              'text-normal-color': currentLeading === item,
            }"
          >
            {{ LeadingMap[item] }}
          </div>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style lang="scss" scoped>
</style>
