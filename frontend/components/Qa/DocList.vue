<script lang="ts" setup>
import type { UploadUserFile } from 'element-plus'
import { QaProgressState, useQaStore } from '~/store/qa'
import type { rowType } from '~/components/Upload2.vue'

const qaStore = useQaStore()
const { qaState } = storeToRefs(qaStore)
const { getFileList } = qaStore
function handleSelect(item: QaDoc) {
  item.selected = !item.selected
  useUpdateQaDocSelect(item._id, qaState.value.seriesId, item.selected)
}

const fileList = ref<UploadUserFile[]>([])
const baseURL = import.meta.env.VITE_API
const uploadUrl = ref(`${baseURL}api/doc_search/upload`)

function handleUploadSuccess() {
  getFileList(qaState.value.seriesId)
}

function handleUploadClose() {
  fileList.value = []
}

function handleUploadCancel(row: rowType) {
  fileList.value = fileList.value.filter(i => i.uid !== row.data.uid)
}

async function handleUploadDelete(row: rowType) {
  fileList.value = fileList.value.filter(i => i.uid !== row.data.uid)
  await useDeleteQaDoc(row.data.response.doc_id, qaState.value.seriesId)
  getFileList(qaState.value.seriesId)
}

const isloading = computed(() => {
  return qaState.value.collection.some(i => i.progress !== QaProgressState.Finish)
})

const uploadData = computed(() => {
  return {
    qa_series_id: qaState.value.seriesId,
  }
})
</script>

<template>
  <div class="w-[340px] h-[calc(100vh-67px)] absolute right-0 top-[59px] flex flex-col">
    <div class="w-full shrink-0 relative">
      <div class="header-title mb-[4px]">
        文件列表
      </div>
    </div>
    <div class="w-full flex-[1_1_0px] pt-[8px] overflow-scroll">
      <div
        v-for="(item, index) in qaState.docs"
        :key="item._id"
        class="item"
      >
        <div class="left">
          <el-checkbox :disabled="isloading" :model-value="item.selected" @update:model-value="handleSelect(item)" />
        </div>
        <div class="right">
          <div class="flex items-center justify-between mb-[4px]">
            <NuxtLink
              :to="`/filePreview?pdfid=${item._id}&fileext=${item.format}&version=v2`"
              target="_blank"
              class="!no-underline"
            >
              <div :title="item.name" class="w-[252px] truncate name">
                {{ item.name }}
              </div>
            </NuxtLink>
            <span class="qa-ref pointer-events-none">{{ index + 1 }}</span>
          </div>
          <div class="date">
            上传时间：{{ timeStamp2String(`${item.date}000`) }}
          </div>
        </div>
      </div>
      <div class="pt-[16px]">
        <Upload2
          v-model:file-list="fileList"
          size="medium"
          :action="uploadUrl"
          :no-list="true"
          :disabled="isloading"
          :data="uploadData"
          @success="handleUploadSuccess"
          @close="handleUploadClose"
          @cancel="handleUploadCancel"
          @delete="handleUploadDelete"
        >
          <el-button class="!text-[rgba(0,0,0,0.6)]" :disabled="isloading">
            继续上传
          </el-button>
        </Upload2>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.header-title {
    font-size: 16px;
    font-weight: 600;
    line-height: 22px;
    color: rgba(0, 0, 0, 0.9);
}

.header-subtitle {
    font-size: 12px;
    font-weight: normal;
    line-height: 20px;
    color: rgba(0, 0, 0, 0.4);
}

.item {
  width: 100%;
  height: 65px;
  display: flex;
  align-items: center;
  padding: 12px 16px;
  padding-left: 0px;
  box-sizing: border-box;
  border-width: 0px 0px 1px 0px;
  border-style: solid;
  border-color: #EBEEF5;

  .left {
    display: flex;
    align-items: center;
  }

  .right {
    padding-left: 16px;
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;

    .name {
      font-size: 14px;
      font-weight: normal;
      line-height: 20px;
      color: rgba(0, 0, 0, 0.9);
    }

    .date {
      font-size: 12px;
      font-weight: normal;
      line-height: 17px;
      color: #606266;

    }
  }
}
</style>
