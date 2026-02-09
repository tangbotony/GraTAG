<script lang="ts" setup>
import type Node from 'element-plus/es/components/tree/src/model/node'

const props = defineProps<{
  value?: [string, string][]
  data?: Tree[]
}>()

const emits = defineEmits<{
  (e: 'update:value', value: [string, string][]): void
}>()

export interface Tree {
  label: string
  children?: Tree[]
  id: string
  value: [string, string][]
  leaf?: boolean
}

function handleNodeClick(data: Tree) {
  emits('update:value', data.value)
}

const treeProps = {
  label: 'label',
  children: 'children',
  isLeaf: 'leaf',
}

async function loadNode(node: Node, resolve: (data: Tree[]) => void) {
  if (node.level === 0) {
    resolve([{
      label: '根目录',
      id: '-1',
      value: [['-1', 'root']],
    }])
    return
  }
  const id = node.data.id

  const { data, error } = await useFetchFolder(id)
  if (!error.value && data.value?.meta) {
    const folders = data.value?.meta.filter(i => i.type === 'folder')
    if (folders?.length === 0)
      return resolve([])

    resolve(folders?.map(f => ({
      label: f.name,
      id: f._id,
      value: f.path,
    })))
  }
}
</script>

<template>
  <div class="tree-container">
    <el-tree
      :props="treeProps"
      node-key="id"
      lazy
      :load="loadNode"
      @node-click="handleNodeClick"
    >
      <template #default="scope">
        <div
          class="flex items-center" :class="{
            'is-selected': props.value ? (props.value[props.value.length - 1][0] === scope.data.id) : false,
          }"
        >
          <div class="i-ll-folder text-normal-color text-[20px]" />
          <span class="text-node-title ml-[4px]">{{ scope.data.label }}</span>
        </div>
      </template>
    </el-tree>
  </div>
</template>

<style lang="scss" scoped>
.tree-container {
    &:deep(.el-tree-node__expand-icon:not(.is-leaf)) {
        color: var(--color-text);
    }

    &:deep(.el-tree-node__content:has(.is-selected)) {
        background-color: #E0E1FF;
    }
}

.text-node-title {
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px; /* 157.143% */
}
</style>
