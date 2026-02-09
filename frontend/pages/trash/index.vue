<script setup lang="ts">
import type { FileType } from '~/composables/api/file'
import type { FolderType } from '~/composables/api/folder'

definePageMeta({
  middleware: 'auth',
  keepalive: true,
  layout: 'base',
  key: 'trash',
})

onActivated(() => {
  fetchTrash()
})

const currentSort = ref('')
function handleSort(val: string) {
  if (currentSort.value === val)
    currentSort.value = ''

  else
    currentSort.value = val
}

const sortedTrashData = computed(() => {
  if (trashState.value.currentData.length === 0)
    return []
  const data = [...trashState.value.currentData]
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
    default:
      return data
  }
})

async function deleteAll() {
  if (sortedTrashData.value.length === 0) {
    ElMessage.warning('废纸篓已经是空的了')
    return
  }
  await useTrashDeleteAll()
  ElMessage.success('清空废纸篓成功')
  await fetchTrash()
}

const moreComp = ref()

const currentFile = ref<FileType | FolderType | undefined>()
const currentMoreLeft = ref(0)
const currentMoreTop = ref(0)
function handleMore(event: Event, file: FileType | FolderType) {
  event.stopPropagation()
  const target = event.target as HTMLElement
  if (!target)
    return
  moreComp.value.close()
  setTimeout(() => {
    const rect = target.getBoundingClientRect()
    currentMoreLeft.value = rect.left
    currentMoreTop.value = rect.top
    currentFile.value = file
    moreComp.value.open()
  }, 200)
}
</script>

<template>
  <div class="flex justify-between shrink-0">
    <div class="flex items-center " />
    <div class="flex">
      <Feedback />
    </div>
  </div>
  <div class=" mt-[30px] pt-[9px] pb-[9px] flex items-center justify-between">
    <span class="text-document-title">废纸篓</span>

    <div class="flex items-center justify-between px-[15px] py-[4px] text-normal-color box" @click="deleteAll">
      <div class="i-ll-edit-delete text-[16px]" />
      <span class="ml-[8px]">清空废纸篓</span>
    </div>
  </div>
  <div v-loading="trashPending && sortedTrashData.length === 0" class="w-full mt-[16px] overflow-x-hidden h-[calc(100vh-166px)] overflow-y-scroll table-container">
    <el-table v-show="sortedTrashData.length > 0 || trashPending" :data="sortedTrashData">
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
          <div class="flex items-center">
            <div
              :class="{
                'i-ll-folder': scope.row.type === 'folder',
                'i-ll-file': scope.row.type === 'document',
              }"
              class="mr-[8.5px] text-normal-color w-[20px] h-[20px]"
            />
            <span>{{ scope.row.name }}</span>
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
      <el-table-column width="174" :formatter="formatterRemainDate">
        <template #header>
          <span class="text-column-title">剩余天数</span>
        </template>
      </el-table-column>
      <el-table-column width="52">
        <template #default="scope">
          <div class="i-ll-more-action text-gray-color cursor-pointer" @click="handleMore($event, scope.row)" />
        </template>
      </el-table-column>
      <template #empty>
        <div />
      </template>
    </el-table>
    <div
      v-show="sortedTrashData.length === 0 && !trashPending"
      class="flex items-center flex-col justify-center w-full h-[calc(100vh-200px)]"
    >
      <img class="w-[200px] h-[200px]" src="~/assets/images/box.png">
      <p class="empty-title mt-[16px]">
        废纸篓为空
      </p>
      <p class="empty-subtitle mt-[8px]">
        删除文件将会保存30天，之后会永久删除
      </p>
    </div>
  </div>
  <TrashMore
    ref="moreComp"
    :file="currentFile"
    :left="currentMoreLeft"
    :top="currentMoreTop"
  />
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

.empty-title {
  color: rgba(0, 0, 0, 0.78);
  text-align: center;
  font-size: 18px;
  font-style: normal;
  font-weight: 500;
  line-height: normal;
  letter-spacing: 0.27px;
}

.empty-subtitle {
  color: rgba(0, 0, 0, 0.36);
  text-align: center;
  font-size: 15px;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
  letter-spacing: 0.225px;
}

.empty-all-text {
  text-align: center;
  font-size: 14px;
  font-style: normal;
  font-weight: 400;
  line-height: 22px; /* 157.143% */
}

.box {
  border-radius: 20px;
  border: 1px solid #4044ED;
  background: #FFF;
  cursor: pointer;
}
</style>
