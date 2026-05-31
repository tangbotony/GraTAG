<script setup lang="ts">
import type { FileType } from '~/composables/api/file'
import type { FolderType } from '~/composables/api/folder'

const props = defineProps<{
  file: FileType | FolderType | null
  left: number
  top: number
}>()

const $emit = defineEmits<{
  (e: 'clicked', operation: string, file: FileType | FolderType): void
}>()
const dropdown1 = ref()

async function handleDelete() {
  if (!props.file)
    return
  if (props.file.type === 'document') {
    await useFileDelete(props.file._id)
  }
  else if (props.file.type === 'folder') {
    const { data, error } = await useFolderDelete(props.file._id)
  }

  ElMessage.success('放入废纸篓成功')
  refreshFolder()
}

// common
function handleCommand(val: string) {
  if (val !== 'delete')
    dropdown1.value?.handleClose()

  if (!props.file)
    return
  $emit('clicked', val, props.file)
}

defineExpose({
  open() {
    dropdown1.value?.handleOpen()
  },
  close() {
    dropdown1.value?.handleClose()
  },
})
</script>

<template>
  <el-dropdown ref="dropdown1" :hide-on-click="false" popper-class="test" trigger="contextmenu" @command="handleCommand">
    <div
      class="fixed pointer-events-none invisible"
      :style="{
        top: `${props.top}px`,
        left: `${props.left}px`,
        width: '1px',
        height: '1px',
      }"
    />
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="rename">
          <span>重命名</span>
        </el-dropdown-item>
        <template v-if="props.file?.type === 'document'">
          <el-dropdown-item command="create-move">
            <span>创建副本到</span>
          </el-dropdown-item>
          <el-dropdown-item command="move">
            <span>移动</span>
          </el-dropdown-item>
        </template>
        <el-dropdown-item command="delete">
          <el-popconfirm
            width="180"
            title="确定移入废纸篓"
            confirm-button-text="确认"
            cancel-button-text="取消"
            @confirm="handleDelete"
          >
            <template #reference>
              <div>放入废纸篓</div>
            </template>
          </el-popconfirm>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style lang="scss" scoped>
</style>
