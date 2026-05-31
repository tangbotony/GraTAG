<script setup lang="ts">
import { EditorContent } from '@tiptap/vue-3'

definePageMeta({
  middleware: 'auth',
  keepalive: true,
  key: 'help',
})

const { editor } = useTiptap({
  editable: false,
  onCreate: () => {
    editor.value?.commands.insertContent(helpArticleHtml(), {
      updateSelection: false,
    })
    editor.value?.commands.focus(1)
  },
})
</script>

<template>
  <div class="w-full h-screen px-10 overflow-y-auto flex justify-center">
    <div class="max-w-[1068px]">
      <EditorContent :editor="editor" />
    </div>
  </div>
</template>
