<script lang="ts" setup>
import type { UploadUserFile } from 'element-plus'
import type { rowType } from './Upload2.vue'

const props = defineProps<{
  fileShowList: { data: UploadUserFile; index: number }[]
  size: string
}>()

const emits = defineEmits<{
  (e: 'delete', row: rowType): void
  (e: 'cancle', row: rowType): void
  (e: 'reUpload', row: rowType): void
}>()

function size2Text(size: number) {
  if (size < 1024 * 1024)
    return `${Number.parseInt(`${size / 1024}`)}k`
  return `${Number.parseInt(`${size / 1024 / 1024}`)}M`
}

function deleteClick(row: rowType) {
  emits('delete', row)
}

function cancleClick(row: rowType) {
  emits('cancle', row)
}

function reUpload(row: rowType) {
  emits('reUpload', row)
}

function handleNameClick(row: rowType) {
  if (row.data.response?.doc_id) {
    navigateTo(`/filePreview?pdfid=${row.data.response.search_doc_id}&fileext=${docType(row)}&version=v2`, {
      open: {
        target: '_blank',
      },
    })
  }
}

function docType(row: rowType) {
  const type = row.data.raw.type.split('/')[1]
  if (type === 'plain')
    return 'txt'
  return 'pdf'
}
</script>

<template>
  <div class="w-full my-table">
    <el-table :data="fileShowList" class="tbfiles" style="width: 100%">
      <el-table-column prop="name" label="文件名">
        <template #default="{ row }">
          <div class="flex items-center">
            <div v-if="row.data.status === 'success' " :title="row.data.response?.msg" class="tableIcon tableIconsuc">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"><path fill="currentColor" d="M512 896a384 384 0 1 0 0-768 384 384 0 0 0 0 768m0 64a448 448 0 1 1 0-896 448 448 0 0 1 0 896" /><path fill="currentColor" d="M745.344 361.344a32 32 0 0 1 45.312 45.312l-288 288a32 32 0 0 1-45.312 0l-160-160a32 32 0 1 1 45.312-45.312L480 626.752l265.344-265.408z" /></svg>
            </div>
            <div v-else-if="row.data.status === 'fail' " :title="row.data.response?.msg" class="tableIcon tableIconfail">
              <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" fill="none" version="1.1" width="20" height="20" viewBox="0 0 20 20"><g><g><path d="M10,1.25C14.8325,1.25,18.75,5.16754,18.75,10C18.75,14.8325,14.8325,18.75,10,18.75C5.16754,18.75,1.25,14.8325,1.25,10C1.25,5.16754,5.16754,1.25,10,1.25ZM10,17.5C14.1422,17.5,17.5,14.1422,17.5,10C17.5,5.85785,14.1422,2.5,10,2.5C5.85785,2.5,2.5,5.85785,2.5,10C2.5,14.1422,5.85785,17.5,10,17.5ZM10.625,11.875L10.625,5.00046L9.375,5.00046L9.375,11.875L10.625,11.875ZM9.24286,13.125L10.7428,13.125L10.7428,14.6249L9.24286,14.6249L9.24286,13.125Z" fill-rule="evenodd" fill="#D54941" fill-opacity="1" /></g></g></svg>
            </div>
            <div v-else-if="row.data.status === 'ready' " class="tableIcon tableIconready">
              <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" fill="none" version="1.1" width="20" height="20" viewBox="0 0 20 20"><g><g><path d="M10,18.75C14.8325,18.75,18.75,14.8325,18.75,10C18.75,5.16751,14.8325,1.25,10,1.25C5.16751,1.25,1.25,5.16751,1.25,10C1.25,14.8325,5.16751,18.75,10,18.75ZM10,2.5C14.1421,2.5,17.5,5.85786,17.5,10C17.5,14.1421,14.1421,17.5,10,17.5C5.85786,17.5,2.5,14.1421,2.5,10C2.5,5.85786,5.85786,2.5,10,2.5ZM9.375,10.48616L9.375,5L10.625,5L10.625,9.96839L13.3842,12.8661L12.5003,13.75L9.375,10.48616Z" fill-rule="evenodd" fill="#000000" fill-opacity="0.6000000238418579" /></g></g></svg>
            </div>
            <div v-else-if="row.data.status === 'uploading'" class="tableIcon tabIconuploading">
              <img src="~/assets/images/generate/refresh.png" class="rotating-image" alt="">
            </div>
            <div class="tableContent cursor-pointer" :title="row.data.name" @click="handleNameClick(row)">
              {{ row.data.name }}
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="size" label="大小" width="90" align="center">
        <template #default="{ row }">
          {{ row.data.size ? size2Text(row.data.size) : '' }}
        </template>
      </el-table-column>
      <el-table-column prop="action" label="操作" align="center" :width="props.size === 'small' ? '86' : '140'">
        <template #default="scope">
          <el-popconfirm
            v-if="scope.row.data.status === 'success'"
            width="200"
            title="确定删除这个文件吗"
            confirm-button-text="确认"
            cancel-button-text="取消"
            @confirm="deleteClick(scope.row)"
          >
            <template #reference>
              <el-button link style="color: #4044ED;">
                删除
              </el-button>
            </template>
          </el-popconfirm>
          <el-button v-else-if="scope.row.data.status === 'uploading'" link style="color: #4044ED;" @click="cancleClick(scope.row)">
            取消上传
          </el-button>
          <el-button v-else-if="scope.row.data.status === 'fail'" link style="color: #4044ED;" @click="reUpload(scope.row)">
            重新上传
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style lang="scss" scoped>
.tableIcon {
  width: 16px;
  height: 16px;
  margin-left: 4px;
  margin-right: 8px;
  cursor: pointer;
  &:deep(.circular) {
    width: 16px;
    height: 16px;
    margin-top: 12px;
  }
  img{ width: 16px; height: 16px;}
}

.rotating-image {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
.tableIcon svg{
  width: 16px; height: 16px;
}

.tabIconuploading{
  img{ width: 14px; height: 14px; margin: 1px;}
}
.tableIconsuc {
  color: #67c23a;
}
.tableContent {
  flex: 1;
  overflow: hidden; /* 确保超出容器的文本被隐藏 */
  white-space: nowrap; /* 防止文本换行 */
  text-overflow: ellipsis; /* 超出部分显示省略号 */
}

.my-table:deep(.el-table thead th) {
  font-size: 14px;
  font-weight: 400;
  line-height: 22px;
  font-weight: normal;
  height: 46px;
  color: rgba(0,0,0,0.4);
}

.my-table:deep(.el-table__row) {
  height: 46px;
}

.my-table:deep(thead th) {
    color:rgba(0,0,0,0.4);
    font-size:14px;
}
</style>
