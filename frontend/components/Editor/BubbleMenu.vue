<script setup lang="ts">
import type { Editor } from '@tiptap/core'
import type { EditorState } from '@tiptap/pm/state'
import { BubbleMenu } from '@tiptap/vue-3'
import { WRITE_STYLE, WRITE_STYLE_LIST } from '~/consts/editor'

const props = defineProps<{
  editor: Editor
  currentArticle: Article
}>()

const $emits = defineEmits<{
  (e: 'change', value: string): void
}>()

const { currentArticle } = toRefs(props)

const functions = ref([
  {
    icon: 'i-ll-edit-continue-writing',
    title: '内容续写',
    type: 'continue',
    open: false,
    click: () => {
      $emits('change', 'continue')
    },
    children: [
      {
        title: '通用模式',
        type: 'continue',
        click: () => {
          $emits('change', 'continue')
        },
      },
      {
        title: '专业模式',
        type: 'continue_profession',
        click: () => {
          $emits('change', 'continue_profession')
        },
      },
    ],
  },
  {
    icon: 'i-ll-edit-expand-writing',
    title: '内容扩写',
    type: 'expand',
    click: () => {
      $emits('change', 'expand')
    },
  },
  {
    icon: 'i-ll-edit-polish-writing',
    title: '内容润色',
    type: 'polish',
    open: false,
    click: () => {
      $emits('change', `polish-${WRITE_STYLE.STRICT}`)
    },
    children: WRITE_STYLE_LIST.map((i) => {
      return {
        title: i.title,
        type: `polish-${i.type}`,
        click: () => {
          $emits('change', `polish-${i.type}`)
        },
      }
    }),
  },
])

let lastMouseDownTarget: HTMLElement | null = null

useEventListener('mousedown', (event: Event) => {
  const target = event.target as HTMLElement
  lastMouseDownTarget = target
})
let proseMirrorContainerDom: undefined | HTMLElement

function shouldShow(props: {
  state: EditorState
  editor: Editor
}) {
  functions.value.forEach((element) => {
    element.open = false
  })
  const { state } = props
  if (state.selection.empty)
    return false

  if (!proseMirrorContainerDom)
    proseMirrorContainerDom = document.querySelector('.ProseMirror') as HTMLElement

  // 区分手动选中和api选中
  if (lastMouseDownTarget && !proseMirrorContainerDom?.contains(lastMouseDownTarget))
    return false

  if (props.editor.isActive('image'))
    return false

  const text = state.doc.textBetween(state.selection.from, state.selection.to)
  if (text.trim().length === 0)
    return false

  return true
}

const listRef = ref()

async function handleOpen(item: any) {
  item.open = !item.open
  await nextTick()
  if (item.type === 'polish' && item.open) {
    listRef.value?.scrollTo({
      top: listRef.value?.scrollHeight,
      behavior: 'smooth',
    })
  }
}
</script>

<template>
  <BubbleMenu
    :editor="props.editor"
    :update-delay="500"
    :tippy-options="{
      popperOptions: {
        modifiers: [
          {
            name: 'flip',
            options: {
              fallbackPlacements: ['auto'],
            },
          },
        ],
      },
    }"
    :should-show="shouldShow"
  >
    <div ref="listRef" class="flex container h-[144px] overflow-scroll">
      <div
        v-for="item in functions"
        :key="item.type"
      >
        <div
          class="item"
          data-stats
          :data-type="`text-${item.type}`"
          @click="item.click"
        >
          <div class="flex items-center py-[9px]">
            <div class="text-[14px] text-normal-color" :class="`${item.icon}`" />
            <span class="text-[14px] leading-[22px] tracking-normal text-[rgba(0,0,0,0.88)] ml-[8px]">{{ item.title }}</span>
            <div class="ml-[16px]" @click.stop>
              <template v-if="item.type === 'continue'">
                <el-switch v-model="currentArticle.isQuote" :width="42" size="small" inline-prompt active-text="引证" inactive-text="引证" />
              </template>
              <template v-if="item.type === 'continue_profession'">
                <el-switch v-model="currentArticle.isQuote" :width="42" size="small" inline-prompt active-text="引证" inactive-text="引证" />
              </template>
            </div>
          </div>
          <div class="w-[33px] h-[42px] flex items-center justify-center" @click.stop="handleOpen(item)">
            <div
              v-if="item.children && item.children.length > 0"
              class="i-ll-arrow-left text-[16px] ml-[4px]"
              :class="{
                'rotate-90': item.open,
                'rotate-270': !item.open,
              }"
            />
          </div>
        </div>
        <div v-if="item.open && item.children && item.children.length > 0" class="children">
          <div
            v-for="child in item.children"
            :key="child.type"
            data-stats
            :data-type="`text-${item.type}`"
            class="child"
            @click="child.click"
          >
            <span class="text-[14px] leading-[22px] tracking-normal select-none ml-[8px]">{{ child.title }}</span>
          </div>
        </div>
      </div>
    </div>
  </BubbleMenu>
</template>

<style lang="scss" scoped>
.container {
    display: flex;
    width: fit-content;
    display: flex;
    flex-direction: column;
    border-radius: 6px;
    padding: 4px;
    gap: 4px;
    background: #FFF;
    box-shadow: 0px 6px 16px 0px rgba(0, 0, 0, 0.08),0px 3px 6px -4px rgba(0, 0, 0, 0.12),0px 9px 28px 8px rgba(0, 0, 0, 0.05);

    .item {
        display: flex;
        padding: 0px 0px 0px 8px;
        cursor: pointer;
        width: 100%;
        align-items: center;
        justify-content: space-between;

        &:hover {
            border-radius: 4px;
            background: #E5E6FF;
        }
    }

    .children {
      background: #F8F8F8;
      border-radius: 4px;
      margin-top: 4px;
      .child {
        cursor: pointer;
        padding: 9px 8px 9px 22px;
        &:hover {
          color: rgb(64, 68, 237);
        }
      }
    }
}
</style>
