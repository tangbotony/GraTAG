<script setup lang="ts">
import type { OnResize, OnScale } from 'vue3-moveable'
import type { Editor } from '@tiptap/vue-3'
import Moveable from 'vue3-moveable'

const props = defineProps<{
  editor: Editor
}>()

function handleResize(e: OnResize) {
  const { target, width, height, delta } = e
  delta[0] && (target!.style.width = `${width}px`)
  delta[1] && (target!.style.height = `${height}px`)
}

async function updateMediaSize() {
  await nextTick()
  const imageInfo = document.querySelector('.ProseMirror-selectednode') as HTMLImageElement
  if (imageInfo) {
    const selection = props.editor.state.selection
    props.editor.chain().focus().setImage({
      width: imageInfo.style.width,
      height: imageInfo.style.height,
    }).setNodeSelection(selection.from).run()
  }
}

function handleResizeEnd() {
  updateMediaSize()
}

function handleScale(e: OnScale) {
  const { target, transform } = e
  target!.style.transform = transform
}

const target = computed(() => {
  const from = props.editor.state.selection.from
  const dom = props.editor.view.nodeDOM(from) as HTMLElement
  return dom
})
</script>

<template>
  <Moveable
    :target="target"
    :container="null"
    :origin="false"
    :edge="false"
    :throttle-drag="1"
    :keep-ratio="true"
    :resizable="true"
    :throttle-resize="1"
    :scalable="true"
    :throttle-scale="1"
    :render-directions="['w', 'e']"
    @resize="handleResize"
    @resize-end="handleResizeEnd"
    @scale="handleScale"
  />
</template>
