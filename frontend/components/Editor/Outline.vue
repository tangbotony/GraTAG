<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'
import { NodeSelection, TextSelection } from '@tiptap/pm/state'
import type { EditorState } from '@tiptap/pm/state'

const props = defineProps<{
  editor?: Editor
  title: string
  container?: HTMLElement
}>()

interface Node {
  from: number
  to: number
  title: string
  level: number
  children?: Node[]
  parent?: Node
  selected: boolean
}

const outline = ref<Node[]>([])

function generateTree(state: EditorState | undefined) {
  if (!state)
    return

  const doc = state.doc
  let currentNode: Node | undefined
  const tree: Node[] = []

  doc.descendants((node, pos, parent) => {
    if (node.type.name === 'heading') {
      const isSelected = state.selection.from >= pos && state.selection.to <= (pos + node.nodeSize)
      const n: Node = {
        from: pos,
        to: pos + node.nodeSize,
        title: node.textContent,
        level: node.attrs.level,
        selected: isSelected,
      }

      if (!currentNode) {
        currentNode = n
        tree.push(currentNode)
      }
      else if (node.attrs.level === currentNode.level) {
        if (currentNode.parent) {
          currentNode.parent.children?.push(n)
          n.parent = currentNode.parent
          currentNode = n
        }
        else {
          tree.push(n)
          currentNode = n
        }
      }
      else if (node.attrs.level > currentNode.level) {
        if (!currentNode.children)
          currentNode.children = []
        currentNode.children.push(n)
        n.parent = currentNode
        currentNode = n
      }
      else if (node.attrs.level < currentNode.level) {
        let isInsert = false
        let parent = currentNode.parent
        while (parent) {
          if (parent.level < node.attrs.level) {
            parent.children?.push(n)
            n.parent = parent
            currentNode = n
            isInsert = true
            break
          }
          else {
            parent = parent.parent
          }
        }

        if (!isInsert) {
          tree.push(n)
          currentNode = n
        }
      }
    }
  })

  outline.value = tree
}

const debounceGenTree = useDebounceFn(generateTree, 300)
watch(() => props.editor?.state, debounceGenTree)

const defaultProps = {
  children: 'children',
  label: 'title',
}

function handleNodecClick(node: Node) {
  if (!props.editor)
    return
  props.editor.commands.focus()

  setTimeout(() => {
    if (!props.editor || !props.container)
      return
    const tr = props.editor.state.tr.setSelection(NodeSelection.create(props.editor?.state.doc, node.from)).scrollIntoView()
    props.editor.view.dispatch(tr)

    const tr_ = props.editor.state.tr.setSelection(TextSelection.create(props.editor?.state.doc, node.from, node.to)).scrollIntoView()
    props.editor.view.dispatch(tr_)

    const dom = props.editor.view.nodeDOM(node.from) as HTMLElement
    const rect = dom.getBoundingClientRect()

    const containerHeight = props.container?.getBoundingClientRect().height || 0
    const expectedPosition = window.innerHeight - (containerHeight / 2)

    const diff = rect.bottom - expectedPosition

    if (diff > 0) {
      props.container?.scrollBy({
        top: diff,
        behavior: 'smooth',
      })
    }
  }, 100)
}

const isVisible = ref(false)

function handleTitle() {
  props.container?.scrollTo({
    top: 0,
    behavior: 'smooth',
  })
}
</script>

<template>
  <section
    :class="{
      'w-[216px]': isVisible,
      'basis-[216px]': isVisible,
      'w-0': !isVisible,
    }"
    class="bg-white transition-all outline-container overflow-hidden shrink-0"
  >
    <div
      class=" flex w-[216px] flex-col items-start overflow-hidden"
    >
      <div class="pl-[24px] h-[48px] flex items-center justify-between w-full border-b-1 border-[rgba(6, 15, 26, 0.07)]">
        <span class="text-[14px] leading-[20px] font-medium text-[rgba(11, 18, 26, 0.6)]">目录</span>
        <div class="i-ll-close text-[16px] cursor-pointer text-gray-400 mr-[19px]" @click="isVisible = false" />
      </div>
      <p class="pl-[24px] mt-[16px] text-[16px] leading-[32px] h-[32px] font-medium cursor-pointer text-left text-[rgba(14, 19, 26, 0.8)] truncate w-full hover:bg-[#f5f7fa]" @click="handleTitle">
        {{ props.title }}
      </p>
      <div class="w-full">
        <el-tree :data="outline" :props="defaultProps" default-expand-all @node-click="handleNodecClick">
          <template #default="{ node, data }">
            <div
              class="truncate text-[14px] leading-[30px]" :class="{
                'is-selected': data.selected,
              }"
            >
              {{ node.label }}
            </div>
          </template>
          <template #empty>
            <div />
          </template>
        </el-tree>
      </div>
    </div>
  </section>
  <div
    class="outline-button" :class="{
      'opacity-100': !isVisible,
      'left-0': !isVisible,
      'left-[-1px]': isVisible,
      'opacity-0': isVisible,
    }"
    @click="isVisible = !isVisible"
  >
    目录
  </div>
</template>

<style lang="scss" scoped>
.outline-button {
  cursor: pointer;
  color: rgba(11, 18, 26, 0.6);
  font-size: 12px;
  font-weight: 500;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  top: calc(50% - 16px);
  line-height: 16px;
  padding: 7px 9px;
  display: block;
  position: fixed;
  margin: 0;
  z-index: 1000;
  background-color: rgb(235, 236, 237);
  border: 1px solid transparent;
  transition: all .15s cubic-bezier(.25,.1,.25,1);
  text-align: center;
  width: 30px;

  &:hover {
    border: 1px solid rgba(7, 15, 26, 0.15);
  }
}

.outline-container {
  .i-ll-close {
    opacity: 0;
  }

  &:hover {
    .i-ll-close {
      opacity: 1;
    }
  }
}

.is-selected {
  color: #4044ED;
}
</style>
