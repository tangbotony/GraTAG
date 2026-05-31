<script setup lang="ts">
import { genFileId } from 'element-plus'
import type { UploadInstance, UploadProps, UploadRawFile } from 'element-plus'
import { token } from '~/composables/common/useCustomFetch'

const $emits = defineEmits<{
  (event: 'response', res: any): void
}>()

const action = `${import.meta.env.VITE_API}/api/analyse`

const isloading = ref(false)

function beforeUpload(file: UploadRawFile) {
  const validTypes = ['doc', 'docx', 'pdf', 'txt']
  const type = file.name.split('.').pop()
  if (type && !validTypes.includes(type)) {
    ElMessage.error('Invalid file type')
    return false
  }

  if (isloading.value)
    return false
  const isLt2M = (file.size / 1024 / 1024) <= 20
  if (!isLt2M)
    ElMessage.error('上传文件大小不能超过 20MB!')

  isloading.value = true
  return isLt2M
}

function onSuceess(res: { res: string }) {
  isloading.value = false
  $emits('response', res.res)
}

function onError() {
  ElMessage.error('上传失败, 请重试')
  isloading.value = false
}

const upload = ref<UploadInstance>()

const handleExceed: UploadProps['onExceed'] = (files) => {
  upload.value!.clearFiles()
  const file = files[0] as UploadRawFile
  file.uid = genFileId()
  upload.value!.handleStart(file)
  upload.value!.submit()
}
</script>

<template>
  <el-upload
    ref="upload"
    :headers="{
      Authorization: `Bearer ${token.token}`,
    }"
    :action="action"
    name="file"
    accept=".doc, .docx, .pdf, .txt"
    :before-upload="beforeUpload"
    :on-error="onError"
    :on-success="onSuceess"
    :limit="1"
    :on-exceed="handleExceed"
    :show-file-list="false"
    :disabled="isloading"
  >
    <button class="bg-transparent w-[16px] h-[16px] cursor-pointer p-0">
      <LoadingIcon v-if="isloading" :width="16" />
      <div v-else class="i-ll-attachment text-[16px] text-[rgba(0,0,0,0.6)]" />
    </button>
    <template #file />
  </el-upload>
</template>
