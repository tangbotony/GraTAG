<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'

const props = defineProps<{
  editor: Editor | undefined
}>()

const items = [
  {
    type: 'left',
    icon: 'i-ll-edit-align-left',
    title: '左对齐',
    action: () => {
      props.editor?.chain().correctBoundary().focus().setTextAlign('left').run()
    },
  },
  {
    type: 'center',
    icon: 'i-ll-edit-align-center',
    title: '居中对齐',
    action: () => {
      props.editor?.chain().correctBoundary().focus().setTextAlign('center').run()
    },
  },
  {
    type: 'right',
    icon: 'i-ll-edit-align-right',
    title: '右对齐',
    action: () => props.editor?.chain().correctBoundary().focus().setTextAlign('right').run(),
  },
  {
    type: 'justify',
    icon: 'i-ll-edit-align-justify',
    title: '两端对齐',
    action: () => props.editor?.chain().correctBoundary().focus().setTextAlign('justify').run(),
  },
]

const currentTextAlign = computed(() => {
  if (props.editor?.isActive({ textAlign: 'left' }))
    return 'left'
  if (props.editor?.isActive({ textAlign: 'center' }))
    return 'center'
  if (props.editor?.isActive({ textAlign: 'right' }))
    return 'right'
  if (props.editor?.isActive({ textAlign: 'justify' }))
    return 'justify'
  return 'left'
})
</script>

<template>
  <el-dropdown trigger="click">
    <button
      class="cursor-pointer flex items-center"
      :class="{
        'text-[rgba(0,0,0,0.87)]': currentTextAlign !== 'left',
        'text-gray-lighter-color': currentTextAlign === 'left',
      }"
    >
      <div
        :class="{
          'i-ll-edit-align-left': currentTextAlign === 'left',
          'i-ll-edit-align-center': currentTextAlign === 'center',
          'i-ll-edit-align-right': currentTextAlign === 'right',
          'i-ll-edit-align-justify': currentTextAlign === 'justify',
        }"
        class="text-[20px]"
      />
      <div class="ml-[4px] i-ll-triangle text-[6px] -rotate-180" />
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="item in items"
          :key="item.type"
          :command="item.type"
        >
          <div
            class="flex items-center text-black-color w-[116px]"
            :class="{
              'is-menu-selected': currentTextAlign === item.type,
            }"
            @click="item.action()"
          >
            <div :class="item.icon" />
            <span class="ml-[8px]">{{ item.title }}</span>
          </div>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style lang="scss" scoped>
.is-menu-selected {
    color: var(--c-text-normal)
}
</style>
