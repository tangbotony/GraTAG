<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'
import { IMAGE_LIMIT_SIZE } from '~/consts/editor'

const props = defineProps<{
  editor: Editor
}>()

const isClear = computed(() => {
  if (
    props.editor?.isActive('font-family') || props.editor?.isActive('font-size')
    || props.editor?.isActive('bold') || props.editor?.isActive('italic') || props.editor?.isActive('underline')
    || props.editor?.isActive('color') || props.editor?.isActive('textStyle')
    || props.editor?.isActive({ lineHeight: /^\d+(\.\d+)?$/ })
    || props.editor?.isActive({ textAlign: 'right' }) || props.editor?.isActive({ textAlign: 'center' }) || props.editor?.isActive({ textAlign: 'justify' })
  )
    return false

  return true
})

// create link
const currentSelectionPosition = reactive({ top: -100000, left: -100000 })

// upload image
const inputFile = ref<HTMLInputElement>()
async function handleUploadChange(e: Event) {
  if (!e.target)
    return
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''
  if (!file)
    return

  if (file.size > IMAGE_LIMIT_SIZE) {
    ElMessage.error('图片大小不能超过 100MB')
    return
  }

  const notification = ElNotification({
    title: '正在上传图片',
    position: 'bottom-right',
    duration: 0,
  })

  const { data } = await useImageUpload(file)
  if (data.value?.image_url)
    props.editor?.commands.insertImage({ src: data.value.image_url })

  notification.close()
}

interface ToolBarItem {
  icon: string
  title: string
  type: string
  action: (value?: any) => void
  status: () => 'disabled' | 'active' | 'inactive'
}
interface Divider {
  type: string
}
const toolbarItems: (ToolBarItem | Divider)[] = [
  {
    icon: 'i-ll-edit-undo',
    title: '撤销',
    type: 'undo',
    action: () => props.editor?.commands.undo(),
    status: () => props.editor?.can().undo() ? 'active' : 'disabled',
  },
  {
    icon: 'i-ll-edit-redo',
    title: '恢复',
    type: 'redo',
    action: () => props.editor?.commands.redo(),
    status: () => props.editor?.can().redo() ? 'active' : 'disabled',
  },
  {
    type: 'divider',
  },
  {
    type: 'font-family',
  },
  {
    type: 'font-size',
  },
  {
    icon: 'i-ll-edit-h1',
    title: '一级标题',
    type: 'heading-1',
    action: () => props.editor?.chain().correctBoundary().focus().toggleHeading({ level: 1 }).run(),
    status: () => props.editor?.isActive('heading', { level: 1 }) ? 'active' : 'inactive',
  },
  {
    icon: 'i-ll-edit-h2',
    title: '二级标题',
    type: 'heading-2',
    action: () => props.editor?.chain().correctBoundary().focus().toggleHeading({ level: 2 }).run(),
    status: () => props.editor?.isActive('heading', { level: 2 }) ? 'active' : 'inactive',
  },
  {
    icon: 'i-ll-edit-h3',
    title: '三级标题',
    type: 'heading-3',
    action: () => props.editor?.chain().correctBoundary().focus().toggleHeading({ level: 3 }).run(),
    status: () => props.editor?.isActive('heading', { level: 3 }) ? 'active' : 'inactive',
  },
  {
    icon: 'i-ll-edit-bold',
    title: '加粗',
    type: 'bold',
    action: () => props.editor?.chain().focus().toggleBold().run(),
    status: () => props.editor?.isActive('bold') ? 'active' : 'inactive',
  },
  {
    icon: 'i-ll-edit-italic',
    title: '斜体',
    type: 'italic',
    action: () => props.editor?.chain().focus().toggleItalic().run(),
    status: () => props.editor?.isActive('italic') ? 'active' : 'inactive',
  },
  {
    icon: 'i-ll-edit-underline',
    title: '下划线',
    type: 'underline',
    action: () => props.editor?.chain().focus().toggleUnderline().run(),
    status: () => props.editor?.isActive('underline') ? 'active' : 'inactive',
  },
  {
    type: 'text-color',
  },
  // {
  //   type: 'highlight-color',
  // },
  {
    type: 'divider',
  },
  {
    icon: 'i-ll-edit-list-number',
    title: '数字编号',
    type: 'ordered-list',
    action: () => props.editor?.chain().correctBoundary().focus().toggleOrderedList().run(),
    status: () => props.editor?.isActive('orderedList') ? 'active' : 'inactive',
  },
  {
    icon: 'i-ll-edit-list-bulleted',
    title: '项目编号',
    type: 'bullet-list',
    action: () => props.editor?.chain().correctBoundary().focus().toggleBulletList().run(),
    status: () => props.editor?.isActive('bulletList') ? 'active' : 'inactive',
  },
  {
    type: 'line-height',
  },
  {
    type: 'align',
  },
  {
    type: 'divider',
  },
  {
    type: 'format-pianter',
  },
  {
    icon: 'i-ll-edit-clear',
    title: '清除格式',
    type: 'clear-format',
    action: () => props.editor?.chain().unsetAllMarks().unsetleading().unsetTextAlign().run(),
    status: () => !isClear.value ? 'active' : 'inactive',
  },
  {
    type: 'divider',
  },
  {
    icon: 'i-ll-edit-image',
    title: '插入图片',
    type: 'image',
    action: () => {
      inputFile.value?.click()
    },
    status: () => props.editor?.isActive('image') ? 'active' : 'inactive',
  },
  {
    icon: 'i-ll-edit-link',
    title: '插入链接',
    type: 'link',
    action: () => {
      if (props.editor?.state.selection.empty) {
        ElMessage.warning('请先选中文字')
        return
      }
      const selectionPosition = getSelectionPostion(props.editor)
      if (selectionPosition) {
        const viewportHeight = document.documentElement.clientHeight
        if ((selectionPosition.top + 88) > viewportHeight)
          currentSelectionPosition.top = selectionPosition.top - 88
        else
          currentSelectionPosition.top = selectionPosition.top + 16 + selectionPosition.height
        currentSelectionPosition.left = selectionPosition.left
      }
    },
    status: () => props.editor?.isActive('link') ? 'active' : 'inactive',
  },
  {
    icon: 'i-ll-edit-quote',
    title: '引用',
    type: 'blockquote',
    action: () => props.editor?.chain()
      .focus()
      .toggleNode('paragraph', 'paragraph')
      .toggleBlockquote()
      .run(),
    status: () => props.editor?.isActive('blockquote') ? 'active' : 'inactive',
  },
]

function handleLinkClosed() {
  currentSelectionPosition.top = -100000
  currentSelectionPosition.left = -100000
}
</script>

<template>
  <div class="flex items-center justify-between px-[24px] pt-[12px] pb-[8px] border-solid border-[rgba(0,0,0,0.05)] border-b-1 h-[40px] toolbar-item">
    <div class="flex items-center">
      <div
        v-for="(item, index) in toolbarItems"
        :key="`${item.type}-${index}`"
        :class="{
          // 'mr-[8px]': [1].includes(index) || item.type === 'divider',
          'ml-[8px]': index !== 0,
        }"
      >
        <template v-if="item.type === 'divider'">
          <span class="divider px-[4px]">|</span>
        </template>
        <template v-else-if="item.type === 'font-family'">
          <EditorFontFamily :editor="props.editor" />
        </template>
        <template v-else-if="item.type === 'font-size'">
          <EditorFontSize :editor="props.editor" />
        </template>
        <template v-else-if="item.type === 'text-color'">
          <EditorColor :editor="props.editor" />
        </template>
        <template v-else-if="item.type === 'align'">
          <EditorTextAlign :editor="props.editor" />
        </template>
        <template v-else-if="item.type === 'format-pianter'">
          <EditorFormatPainter :editor="props.editor" />
        </template>
        <template v-else-if="item.type === 'line-height'">
          <EditorLeadingAdjust :editor="props.editor" />
        </template>
        <template v-else-if="item.type === 'highlight-color'">
          <EditorMark :editor="props.editor" />
        </template>
        <template v-else>
          <el-tooltip
            :content="(item as ToolBarItem).title"
          >
            <button
              :disabled="(item as ToolBarItem).status() === 'disabled'"
              :class="{
                'is-active': (item as ToolBarItem).status() === 'active',
                'cursor-pointer': (item as ToolBarItem).status() !== 'disabled',
                'cursor-not-allowed': (item as ToolBarItem).status() === 'disabled',
              }"
              @click="(item as ToolBarItem).action()"
            >
              <div :class="`${(item as ToolBarItem).icon} text-[20px] text-gray-lighter-color`" />
            </button>
          </el-tooltip>
        </template>
      </div>
    </div>
    <div>
      <EditorWordCount :editor="props.editor" />
    </div>
  </div>
  <EditorLinkCreate v-if="props.editor" :editor="props.editor" :current-selection-position="currentSelectionPosition" @closed="handleLinkClosed" />
  <EditorLinkEdit v-if="props.editor" :editor="props.editor" />
  <input ref="inputFile" class="hidden" type="file" accept="image/png, image/jpg, image/jpeg, image/gif" @change="handleUploadChange">
</template>

<style lang="scss" scoped>
.toolbar-item {
  button, &:deep(button) {
    border: none;
    outline: none;
    background: none;
    border-radius: 4px;
    padding: 4px;
    &:hover {
      background-color: #F0F0F0;
    }

    &:hover div {
      color: rgba(0, 0, 0, 0.87);
    }
  }

  .divider {
    color: var(--c-text-gray-lighter, rgba(0, 0, 0, 0.45));
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 20px; /* 157.143% */
  }
  .is-active, &:deep(.is-active) {
    background-color: #F0F0F0;
    border-radius: 4px;

    div {
      color: rgba(0, 0, 0, 0.87);
    }
  }
}
</style>
