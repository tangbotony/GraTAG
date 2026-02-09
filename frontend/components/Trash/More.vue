<script setup lang="ts">
import type { FileType } from '~/composables/api/file'
import type { FolderType } from '~/composables/api/folder'

const props = defineProps<{
  file: FolderType | FileType | undefined
  left: number
  top: number
}>()
const dropdown1 = ref()

async function handleCommand(type: string) {
  if (type !== 'delete')
    dropdown1.value?.handleClose()

  if (!props.file)
    return

  if (type === 'recover') {
    if (props.file.type === 'folder')
      await useTrashRecoverFolder(props.file._id)

    else if (props.file.type === 'document')
      await useTrashRecoverFile(props.file._id)

    ElMessage.success('还原成功')
    await fetchTrash()
  }
}

async function handleDelete() {
  if (!props.file)
    return
  if (props.file.type === 'folder')
    await useTrashDeleteFolder(props.file._id)

  else if (props.file.type === 'document')
    await useTrashDeleteDocument(props.file._id)

  ElMessage.success('彻底删除成功')
  await fetchTrash()
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
  <el-dropdown ref="dropdown1" :hide-on-click="false" trigger="contextmenu" @command="handleCommand">
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
        <el-dropdown-item command="recover">
          <div>还原</div>
        </el-dropdown-item>
        <el-dropdown-item command="delete">
          <el-popconfirm
            width="236"
            title="文件被删除后将无法恢复，确定删除吗？"
            confirm-button-text="确认"
            cancel-button-text="取消"
            @confirm="handleDelete()"
          >
            <template #reference>
              <div>彻底删除</div>
            </template>
          </el-popconfirm>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>
