<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'

const props = defineProps<{
  editor: Editor | undefined
}>()

const status = computed(() => {
  const formatPainter = props.editor?.storage.formatPainter
  return (formatPainter.type || (formatPainter.marks.length > 0)) ? 'active' : 'inactive'
})

function handleAction() {
  const formatPainter = props.editor?.storage.formatPainter
  const isSaved = formatPainter.type || (formatPainter.marks.length > 0)
  if (isSaved)
    props.editor?.chain().focus().clearSavedFormat().run()

  else
    props.editor?.chain().focus().getFormat().run()
}

useEventListener('click', (event: Event) => {
  const formatPainter = props.editor?.storage.formatPainter
  if (!(formatPainter.type || (formatPainter.marks.length > 0)))
    return

  const target = event.target as HTMLElement
  if (!target)
    return
  const containerDom = document.querySelector('.ProseMirror') as HTMLElement
  const isIncludes = containerDom!.contains(target)
  if (!isIncludes)
    return
  const selection = props.editor?.state.selection
  if (!selection)
    return

  props.editor?.chain().focus().setFormat(selection.from, selection.to).clearSavedFormat().run()
})
</script>

<template>
  <el-tooltip
    content="格式刷"
  >
    <button

      :class="{
        'is-active': status === 'active',
      }"
      @click="handleAction"
    >
      <div class="i-ll-piant-brush text-[18px] text-gray-lighter-color" />
    </button>
  </el-tooltip>
</template>
