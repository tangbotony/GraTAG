<script setup lang="ts">
import type { FileType } from '~/composables/api/file'
import type { FolderType } from '~/composables/api/folder'

const props = defineProps<{
  file: FileType | FolderType | null
  operation: string
}>()

const $emits = defineEmits<{
  (e: 'closed'): void
}>()

const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogMoveVisible = ref(false)
const dialogMoveTitle = ref('')
const isloading = false

watch(() => props.operation, (val) => {
  if (val && props.file) {
    switch (val) {
      case 'rename':
        rename(props.file)
        dialogVisible.value = true
        break
      case 'create-move':
        createMove()
        dialogMoveVisible.value = true
        break
      case 'move':
        move()
        dialogMoveVisible.value = true
        break
      case 'delete':
        break
    }
  }
})

// 重命名
const name = ref('')
function rename(file: FileType | FolderType) {
  if (file.type === 'document')
    dialogTitle.value = '修改文件名称'

  else if (file.type === 'folder')
    dialogTitle.value = '修改文件夹名称'
}
async function renameSave(file: FileType | FolderType | null) {
  if (!file)
    return
  if (file.type === 'document') {
    const { error } = await useFileUpdate({ name: name.value, id: file._id })
    if (!error.value)
      refreshFolder()
  }
  else if (file.type === 'folder') {
    const { error } = await useFolderUpdate({ name: name.value, id: file._id })
    if (!error.value)
      refreshFolder()
  }

  dialogVisible.value = false
}

// 创建移动到
const selectedFolder = ref<[string, string][] | undefined>(undefined)
function createMove() {
  dialogMoveTitle.value = '创建副本到'
}
async function createMoveOk() {
  if (props.file && selectedFolder.value) {
    if (props.file.type === 'document') {
      const { data, error } = await useFileCreate({
        name: `${props.file.name} 副本`,
        parent_id: selectedFolder.value[selectedFolder.value.length - 1][0],
        text: (props.file as FileType).text || '',
        plain_text: (props.file as FileType).plain_text || '',
      })
      if (!error.value) {
        moveFilePath(selectedFolder.value, selectedFolder.value[selectedFolder.value.length - 1])
        ElMessage({
          message: '创建副本成功',
          type: 'success',
        })
        refreshFolder()
      }
    }
  }
  dialogMoveVisible.value = false
}
function createMoveCancel() {
  dialogMoveVisible.value = false
}

// 移动到
function move() {
  dialogMoveTitle.value = '移动到'
}

function moveCancel() {
  dialogMoveVisible.value = false
}

async function moveOk() {
  if (props.file && selectedFolder.value) {
    if (props.file.type === 'document') {
      const { error } = await useFileUpdate({
        id: props.file._id,
        parent_id: selectedFolder.value[selectedFolder.value.length - 1][0],
      })
      if (!error.value) {
        moveFilePath(selectedFolder.value, selectedFolder.value[selectedFolder.value.length - 1])
        ElMessage({
          message: '移动成功',
          type: 'success',
        })
      }
    }
  }
  dialogMoveVisible.value = false
}

// common
function closed() {
  name.value = ''
  selectedFolder.value = undefined
  $emits('closed')
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="dialogTitle"
    :width="425"
    append-to-body
    @closed="closed"
  >
    <div class="w-full h-[334px] overflow-y-scroll">
      <div v-if="props.operation === 'rename'" class="w-full">
        <el-input
          v-model="name"
          maxlength="20"
          show-word-limit
          type="text"
          placeholder="请输入文件夹名称"
        />
      </div>
    </div>
    <template #footer>
      <div class="flex items-center justify-end">
        <template v-if="props.operation === 'rename'">
          <el-button :loading="isloading" :disabled="name.length === 0" @click="renameSave(props.file)">
            保存
          </el-button>
        </template>
      </div>
    </template>
  </el-dialog>

  <el-dialog
    v-model="dialogMoveVisible"
    :title="dialogMoveTitle"
    :width="425"
    append-to-body
    destroy-on-close
    @closed="closed"
  >
    <div v-if="props.operation === 'create-move' || props.operation === 'move'" class="w-full">
      <FileFolderTree v-model:value="selectedFolder" />
    </div>
    <template #footer>
      <div class="flex items-center justify-end">
        <template v-if="props.operation === 'create-move'">
          <el-button class="cancel-btn" @click="createMoveCancel">
            取消
          </el-button>
          <el-button :loading="isloading" :disabled="!selectedFolder" @click="createMoveOk">
            确认
          </el-button>
        </template>
        <template v-if="props.operation === 'move'">
          <el-button :loading="isloading" @click="moveCancel">
            取消
          </el-button>
          <el-button :loading="isloading" :disabled="!selectedFolder" @click="moveOk">
            确认
          </el-button>
        </template>
      </div>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
.cancel-btn {
  background-color: rgba(0,0,0,0.1) !important;
  color: rgba(0,0,0,0.85) !important;
  border: 1px solid rgba(0,0,0,0.1) !important;
}
</style>
