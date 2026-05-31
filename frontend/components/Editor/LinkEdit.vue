<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'

const props = defineProps<{
  editor: Editor
}>()
const currentClickedPosition = reactive({
  left: -100000,
  top: -100000,
})

const link = ref('')

watch(() => props.editor.state.selection, (val) => {
  if (!props.editor.isActive('link'))
    return

  const rect = getSelectionPostion(props.editor)
  const viewportHeight = document.documentElement.clientHeight
  currentClickedPosition.left = rect.left

  if (rect.top + 16 + rect.height + 56 > viewportHeight)
    currentClickedPosition.top = rect.top - 16 - 56

  else
    currentClickedPosition.top = rect.top + 16 + rect.height
  link.value = props.editor.getAttributes('link').href || ''
})

const isEdit = ref(false)

const wrapper = ref()
onClickOutside(wrapper, () => {
  closed()
})

function closed() {
  isEdit.value = false
  link.value = ''
  currentClickedPosition.left = -100000
  currentClickedPosition.top = -100000
}

function handleEdit() {
  isEdit.value = true
}

function save() {
  const state = props.editor.state
  const dispatch = props.editor.view.dispatch
  if (!state || !dispatch)
    return

  state.doc.nodesBetween(state.selection.from, state.selection.to, (node, pos) => {
    const mark = node.marks.find(m => m.type.name === 'link')
    if (!mark)
      return
    const tr = state.tr.addMark(pos, pos + node.nodeSize, state.schema.marks.link.create({ href: link.value }))
    dispatch(tr)
    closed()
  })
}

const { copy } = useClipboard()
async function handleCopy() {
  try {
    await copy(link.value)
    ElMessage.success('复制成功')
  }
  catch (error) {
    ElMessage.error('复制失败')
  }
}

function handleDelete() {
  const state = props.editor.state
  const dispatch = props.editor.view.dispatch
  if (!state || !dispatch)
    return

  state.doc.nodesBetween(state.selection.from, state.selection.to, (node, pos) => {
    const mark = node.marks.find(m => m.type.name === 'link')
    if (!mark)
      return
    const tr = state.tr.removeMark(pos, pos + node.nodeSize, state.schema.marks.link)
    dispatch(tr)
    closed()
  })
}

function go() {
  window.open(link.value, '_blank')
}
const inputRef = ref()
watch(isEdit, async (val) => {
  if (val) {
    await nextTick()
    inputRef.value?.focus()
  }
})
</script>

<template>
  <div
    ref="wrapper"
    class="fixed flex items-center justify-between p-[16px] box-border w-[409px] z-10 rounded-[8px] bg-white shadow-[0_2px_8px_0_rgba(0,0,0,0.15)]"
    :style="{
      left: `${currentClickedPosition.left}px`,
      top: `${currentClickedPosition.top}px`,
    }"
  >
    <template v-if="isEdit">
      <el-input ref="inputRef" v-model="link" autofocus placeholder="请输入网址" style="width: 277px;" />
    </template>
    <template v-else>
      <div class="text-link truncate cursor-pointer" @click="go">
        {{ link }}
      </div>
    </template>

    <template v-if="!isEdit">
      <div class="flex items-center">
        <button class="hover:bg-[#F1F1F1] cursor-pointer" @click="handleEdit">
          <div class="i-ll-edit-edit text-[24px] hover:text-black text-[rgba(0,0,0,0.45)]" />
        </button>
        <button class=" hover:bg-[#F1F1F1] cursor-pointer ml-[8px]" @click="handleCopy">
          <div class="i-ll-edit-copy text-[24px] hover:text-black text-[rgba(0,0,0,0.45)]" />
        </button>
        <button class=" hover:bg-[#F1F1F1] cursor-pointer ml-[8px]">
          <div class="i-ll-edit-delete text-[24px] hover:text-black text-[rgba(0,0,0,0.45)]" @click="handleDelete" />
        </button>
      </div>
    </template>
    <template v-else>
      <el-button :disabled="link.length === 0" class="base-btn" @click="save">
        <span class="text-ok">确认</span>
      </el-button>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.text-link {
  color: #4044ED;
  font-size: 14px;
  font-style: normal;
  font-weight: 400;
  line-height: 22px; /* 157.143% */
  text-decoration-line: underline;
  width: 266px;
}

button {
  border: none;
  outline: none;
  background: none;
  padding: 0;
  border-radius: 4px;
}
</style>
