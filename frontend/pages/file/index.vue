<script setup lang="ts">
import type { FileType } from '~/composables/api/file'
import type { FolderType } from '~/composables/api/folder'
import { refreshFolder } from '~/composables/folder'

definePageMeta({
  middleware: 'auth',
  keepalive: true,
  layout: 'base',
  key: 'file',
})

const tabledata = computed(() => {
  return fileState.value.currentData
})

const currentSort = ref('')

const sortedTableData = computed(() => {
  if (!tabledata.value)
    return []
  const data = [...tabledata.value]
  switch (currentSort.value) {
    case 'name-folder':
      return data.sort((a, b) => {
        if (a.type === b.type)
          return 0
        if (a.type === 'folder')
          return -1
        return 1
      })
    case 'name-asc':
      return data.sort((a, b) => {
        if (a.name === b.name)
          return 0
        if (a.name > b.name)
          return 1
        return -1
      })
    case 'name-desc':
      return data.sort((a, b) => {
        if (a.name === b.name)
          return 0
        if (a.name > b.name)
          return -1
        return 1
      })
    case 'date-asc':
      return data.sort((a, b) => {
        if (a.update_time === b.update_time)
          return 0
        if (a.update_time > b.update_time)
          return 1
        return -1
      })
    case 'date-desc':
      return data.sort((a, b) => {
        if (a.update_time === b.update_time)
          return 0
        if (a.update_time > b.update_time)
          return -1
        return 1
      })
    default:
      return data
  }
})

function handleSort(val: string) {
  if (currentSort.value === val)
    currentSort.value = ''

  else
    currentSort.value = val
}

const currentOperation = ref('')
const currentFile = ref<null | FolderType | FileType>(null)
function handleMore(val: string, file: FolderType | FileType) {
  currentOperation.value = val
}
function handleFileMoreClosed() {
  currentOperation.value = ''
  currentFile.value = null
}

function handleRowClick(row: FileType | FolderType) {
  if (row.type === 'folder')
    pushFilePath([row._id, row.name])

  else if (row.type === 'document')
    navigateTo(`/document/${row._id}`)
}

function handlePathClick(to: [string, string]) {
  moveFilePath(fileState.value.stack, to)
}

onActivated(() => {
  refreshFolder()
})

const FillMoreLeft = ref(-100000)
const FillMoreTop = ref(-100000)
const moreComp = ref()
async function handleFileClickd(event: Event, row: FileType | FolderType) {
  event.stopPropagation()
  const target = event.target as HTMLElement
  if (!target)
    return
  moreComp.value.close()
  setTimeout(() => {
    const rect = target.getBoundingClientRect()
    FillMoreLeft.value = rect.left
    FillMoreTop.value = rect.top
    currentFile.value = row
    moreComp.value.open()
  }, 200)
}

async function handleFileCreated(type: string) {
  if (type === 'folder')
    refreshFolder()
}
</script>

<template>
  <div class="flex justify-between shrink-0">
    <div class="flex items-center ">
      <FileSearch />
    </div>
    <div class="flex">
      <Feedback />
    </div>
  </div>
  <div class="w-full pt-[24px] pb-[33px]">
    <FileCreate :parent-id="fileState.currentFolder" @created="handleFileCreated" />
  </div>
  <p class="pb-[9px] shrink-0">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item v-for="(s, index) in fileState.stack" :key="s[0]">
        <div
          class="text-document-title path cursor-pointer"
          :class="{
            'path-selected': index === (fileState.stack.length - 1),
            'pointer-events-none': index === (fileState.stack.length - 1),
          }"
          @click="handlePathClick(s)"
        >
          {{ s[1] === 'root' ? '我的文档' : s[1] }}
        </div>
      </el-breadcrumb-item>
    </el-breadcrumb>
  </p>
  <div v-loading="filePending && sortedTableData.length === 0" class="w-full mt-[16px] h-[calc(100vh-300px)] overflow-y-auto table-container">
    <el-table :data="sortedTableData">
      <el-table-column>
        <template #header>
          <el-dropdown @command="handleSort">
            <div
              class="flex items-center cursor-pointer" :class="{
                'text-normal-color': currentSort.startsWith('name'),
                'text-gray-color': !currentSort.startsWith('name'),
              }"
            >
              <span class="text-column-title">名称</span>
              <div class="i-ll-arrow-bottom ml-[4px]" />
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="name-folder">
                  <span
                    :class="{
                      'text-normal-color': currentSort === 'name-folder',
                    }"
                  >文件夹优先</span>
                </el-dropdown-item>
                <el-dropdown-item command="name-asc">
                  <span
                    :class="{
                      'text-normal-color': currentSort === 'name-asc',
                    }"
                  >名称（A -> Z）</span>
                </el-dropdown-item>
                <el-dropdown-item command="name-desc">
                  <span
                    :class="{
                      'text-normal-color': currentSort === 'name-desc',
                    }"
                  >
                    名称（Z -> A）
                  </span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template #default="scope">
          <div
            class="flex items-center cursor-pointer"
            @click="handleRowClick(scope.row)"
          >
            <div
              :class="{
                'i-ll-folder': scope.row.type === 'folder',
                'i-ll-file': scope.row.type === 'document',
              }"
              class="mr-[8.5px] text-normal-color w-[20px] h-[20px] shrink-0"
            />
            <div class="truncate flex-1">
              {{ scope.row.name }}
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column width="174">
        <template #header>
          <span class="text-column-title">所有者</span>
        </template>
        <template #default>
          <span>我</span>
        </template>
      </el-table-column>
      <el-table-column prop="updateTime" label="编辑时间" width="174" :formatter="formatterDate">
        <template #header>
          <el-dropdown @command="handleSort">
            <div
              class="flex items-center cursor-pointer" :class="{
                'text-normal-color': currentSort.startsWith('date'),
                'text-gray-color': !currentSort.startsWith('date'),
              }"
            >
              <span class="text-column-title">编辑时间</span>
              <div class="i-ll-arrow-bottom ml-[4px]" />
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="date-asc">
                  <span
                    :class="{
                      'text-normal-color': currentSort === 'date-asc',
                    }"
                  >编辑时间从远到近</span>
                </el-dropdown-item>
                <el-dropdown-item command="date-desc">
                  <span
                    :class="{
                      'text-normal-color': currentSort === 'date-desc',
                    }"
                  >编辑时间从近到远</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
      <el-table-column width="52">
        <template #default="scope">
          <div class="flex items-center justify-center">
            <div class="i-ll-more-action text-gray-color cursor-pointer" @click="handleFileClickd($event, scope.row)" />
          </div>
        </template>
      </el-table-column>
      <template #empty>
        <div v-if="!filePending" class="flex items-center justify-center pt-[36px] pb-[36px]">
          <img class="w-[121px] h-[130px]" src="~/assets/images/empty.png">
        </div>
        <div v-else />
      </template>
    </el-table>
    <FileMore
      ref="moreComp"
      :file="currentFile"
      :left="FillMoreLeft"
      :top="FillMoreTop"
      @clicked="handleMore"
      @deleted="handleFileMoreClosed"
    />
    <FileMoreDialogs :file="currentFile" :operation="currentOperation" @closed="handleFileMoreClosed" />
  </div>
</template>

<style lang="scss" scoped>
.text-document-title {
  font-size: 20px;
  font-style: normal;
  line-height: 22px; /* 110% */
}

.text-column-title {
  font-size: 12px;
  font-style: normal;
  font-weight: 500;
  line-height: 22px; /* 183.333% */
}

.table-container {
  .el-tooltip__trigger {
    outline: none !important
  }
}

.path {
  color: rgba(0, 0, 0, 0.45);
  font-weight: 400;
  padding: 8px 4px;

  &:hover {
    background-color: #F0F0F0;
    border-radius: 4px;
  }
}

.path.path-selected {
  color: rgba(0, 0, 0, 0.85);
  font-weight: 500;
}
</style>
