<script lang="ts" setup>
import type { Editor } from '@tiptap/vue-3'

const props = defineProps<{
  editor: Editor
  currentSelectionPosition: { top: number; left: number }
}>()

const emits = defineEmits<{
  (e: 'closed'): void
}>()

const link = ref('')

function ok() {
  let linkText = link.value
  if (!linkText.startsWith('http') && !linkText.startsWith('https'))
    linkText = `https://${linkText}`

  props.editor.chain().focus().setLink({ href: linkText }).run()
  link.value = ''
  emits('closed')
}

const wrapper = ref()
onClickOutside(wrapper, () => {
  link.value = ''
  emits('closed')
})
const inputRef = ref()
watch(() => props.currentSelectionPosition.left, (val) => {
  if (val > 0)
    inputRef.value?.focus()
})
</script>

<template>
  <div
    ref="wrapper"
    class="fixed flex items-center justify-between p-[16px] box-border w-[409px] z-10 rounded-[8px] bg-white shadow-[0_2px_8px_0_rgba(0,0,0,0.15)]"
    :style="{
      left: `${currentSelectionPosition.left}px`,
      top: `${currentSelectionPosition.top}px`,
    }"
  >
    <el-input ref="inputRef" v-model="link" autofocus placeholder="请输入网址" style="width: 277px;" />

    <el-button :disabled="link.length === 0" class="base-btn" @click="ok">
      <span class="text-ok">确认</span>
    </el-button>
  </div>
</template>

<style lang="scss" scoped>
.text-ok {
    text-align: center;
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px; /* 157.143% */
}
</style>
