<script setup lang="ts">
import type { UploadFile, UploadFiles, UploadUserFile } from 'element-plus'
import Token from '~/lib/token'

const props = defineProps<{
  fileList: UploadUserFile[]
  size: 'small' | 'medium'
  action: string
  data?: Record<string, any>
  drag?: boolean
  noList?: boolean
  disabled?: boolean
}>()
const $emits = defineEmits<{
  (e: 'success'): void
  (e: 'close'): void
  (e: 'cancel', row: rowType): void
  (e: 'delete', row: rowType): void
  (e: 'update:file-list', value: UploadUserFile[]): void
}>()

const dialogFileVisible = ref(false)
const isEnv = import.meta.env.VITE_ENV === 'sit'
const token = new Token(isEnv ? 'dev' : 'prod')
const upload = ref()

const { fileList } = toRefs(props)

interface UploadRawFile extends File {
  uid: number
  date: number
}
const fileFailList = ref<UploadUserFile[]>([])

const fileShowList = computed(() => {
  const allFile = fileList.value.concat(fileFailList.value)
  allFile.sort((a, b) => {
    // eslint-disable-next-line @typescript-eslint/prefer-ts-expect-error
    // @ts-ignore 上传文件的日期
    if (a.raw.date && b.raw.date)
      // eslint-disable-next-line @typescript-eslint/prefer-ts-expect-error
      // @ts-ignore 上传文件的日期
      return b.raw.date - a.raw.date

    return 0
  })
  return allFile.map((v, i) => ({ data: v, index: i }))
})

const fileShowListBrief = computed(() => {
  if (props.size === 'small')
    return fileShowList.value.slice(0, 5)
  return fileShowList.value
})

let uploadingSum = 0
type Resolve = (value: any) => void
const waitingQueue: Resolve[] = []
const concurrencylimitation = 3
const maxFileSize = 1024 * 1024 * 300

const allSize = computed(() => {
  return fileList.value.reduce((acc, file) => {
    if (file.size && file.status !== 'fail')
      return acc + file.size
    return acc
  }, 0)
})

function handleChange(uploadFile: UploadFile, uploadFiles: UploadFiles) {
  // eslint-disable-next-line @typescript-eslint/prefer-ts-expect-error
  // @ts-ignore 上传文件的日期
  if (uploadFile.status === 'fail')
    fileFailList.value.push(uploadFile)

  if (uploadFile.status === 'fail' || uploadFile.status === 'success') {
    uploadingSum -= 1
    const resolve = waitingQueue.shift()
    if (resolve) {
      resolve(true)
      uploadingSum += 1
    }
  }
}

const dialogNoListVisible = ref(false)
watch(dialogNoListVisible, (v) => {
  if (!v)
    $emits('close')
})

async function beforeUpload(rawFile: UploadRawFile) {
  if (props.noList)
    dialogNoListVisible.value = true

  if (!rawFile.date)
    rawFile.date = new Date().getTime()

  if (allSize.value > maxFileSize) {
    ElMessage({
      message: `文件大小超过300M,已超出${size2Text(allSize.value - maxFileSize)}`,
      type: 'error',
    })
    return false
  }

  if (uploadingSum < concurrencylimitation) {
    uploadingSum += 1
    return true
  }
  if (uploadingSum >= concurrencylimitation) {
    await new Promise((resolve: Resolve) => {
      waitingQueue.push(resolve)
    })
  }

  return true
}

function handleExceed() {
  ElMessage({
    message: '总文件数量不能超过100个',
    type: 'error',
  })
}

function handleSuccess(response: any, uploadFile: UploadFile) {
  $emits('success')
}
function handleError(error: any, uploadFile: UploadUserFile) {
  ElMessage({
    message: `${uploadFile.name} -- ${JSON.parse(error.message).message}`,
    type: 'error',
  })
}

export interface rowType {
  data: {
    uid: number
    raw: File
    response: any
  }
}

function cancleClick(row: rowType) {
  $emits('cancel', row)
  upload.value.handleRemove(row.data)
}

function deleteClick(row: rowType) {
  $emits('delete', row)
}

function seeAllClick() {
  dialogFileVisible.value = true
}

function handleFileList(value: UploadUserFile[]) {
  $emits('update:file-list', value)
}

function size2Text(size: number) {
  if (size < 1024 * 1024)
    return `${Number.parseInt(`${size / 1024}`)}k`
  return `${Number.parseInt(`${size / 1024 / 1024}`)}M`
}

async function reUpload(value: rowType) {
  fileFailList.value = fileFailList.value.filter(v => v.uid !== value.data.uid)
  upload.value.handleStart(value.data.raw)
  await nextTick()
  upload.value.submit()
}
const container = ref()

function goOnUpload() {
  const dom = container.value?.querySelector('.el-upload__input')
  if (dom)
    dom.click()
}
</script>

<template>
  <div ref="container" class="container">
    <el-upload
      ref="upload"
      :file-list="fileList"
      class="upload-demo"
      :action="props.action"
      :data="props.data || {}"
      multiple
      :show-file-list="false"
      :on-success="handleSuccess"
      :on-error="handleError"
      :before-upload="beforeUpload"
      :on-change="handleChange"
      :on-exceed="handleExceed"
      accept=".pdf,.docx,.doc,.txt"
      :headers="{ Authorization: `Bearer ${token.token}` }"
      :limit="101"
      :drag="!!props.drag"
      :disabled="props.disabled"
      @update:file-list="handleFileList"
    >
      <template v-if="props.drag">
        <div class="drag-box">
          <div class="i-ll-upload-box text-[26.34px] text-[#4044ED] mb-[12.68px]" />
          <div class="text-[14px] leading-[20px] font-noraml flex justify-center items-center mb-[4px]">
            <span class="text-[#4044ED]">点击此处</span><span class="text-[rgba(0,0,0,0.9)]">或将文件拖拽到此区域</span>
          </div>
          <div class="flex justify-center items-center leading-[20px] leading-normal text-[12px] text-[rgba(0,0,0,0.4)]">
            支持导入pdf、docx、doc、txt 4种格式，最多上传100个文件，总大小不超过300M
          </div>
        </div>
      </template>
      <template v-else>
        <slot />
      </template>
      <template #tip>
        <template v-if="!props.drag && !props.noList">
          <div class="el-upload__tip" style="line-height:20px ;color:rgba(0,0,0,0.4);font-weight: normal;">
            支持导入pdf、docx、doc、txt 格式，最多上传100个文件，总大小不超过300M
          </div>
        </template>
      </template>
    </el-upload>
  </div>
  <template v-if="!props.noList && fileShowListBrief.length > 0">
    <Upload2List
      :file-show-list="fileShowListBrief"
      :size="props.size"
      @delete="deleteClick"
      @cancle="cancleClick"
      @re-upload="reUpload"
    />
  </template>
  <template v-if="props.size === 'small'">
    <div v-if="fileShowList.length > 5" class="flex pt-[8px]">
      <div style="color: #4044ED;cursor: pointer;margin-right: 10px;" @click="seeAllClick">
        查看全部
      </div>
      <div style="color:rgba(0,0,0,0.6)">
        ( 共{{ fileShowList.length }}个 )
      </div>
    </div>
    <el-dialog v-model="dialogFileVisible" title="已上传文件" width="800" append-to-body>
      <template v-if="fileShowList.length > 0">
        <div class="w-full h-[350px] overflow-scroll">
          <Upload2List
            :file-show-list="fileShowList"
            size="medium"
            @delete="deleteClick"
            @cancle="cancleClick"
            @re-upload="reUpload"
          />
        </div>
      </template>
      <template #footer>
        <div class="numerfoot">
          共{{ fileShowList.length }}个文件
        </div>
      </template>
    </el-dialog>
  </template>

  <template v-if="props.noList">
    <el-dialog v-model="dialogNoListVisible" title="上传文件" width="600" append-to-body>
      <div class="w-full h-[350px] overflow-scroll">
        <Upload2List
          :file-show-list="fileShowList"
          size="medium"
          @delete="deleteClick"
          @cancle="cancleClick"
          @re-upload="reUpload"
        />
      </div>
      <template #footer>
        <div class="flex items-center justify-between">
          <span class="numerfoot">共{{ fileShowList.length }}个文件</span>
          <div class="flex items-center">
            <el-button type="primary" @click="goOnUpload">
              继续上传
            </el-button>
            <el-button @click="dialogNoListVisible = false">
              完成
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </template>
</template>

<style lang="scss" scoped>
.drag-box {
    width: 700px;
    height: 160px;
    border-radius: 12px;
    background: #FAFAFD;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    box-sizing: border-box;
    border: 1px dashed #D9E1FF;

}

.container {
    &:deep(.el-upload-dragger) {
        background: transparent;
        border: none;
        padding: 0px;
        border-radius: 0px;
    }
}

.numerfoot{
  text-align: left;
  font-size: 14px;
  color:rgba(0,0,0,0.4);
  height: 32px;
  display: flex;
  align-items: center
}
</style>
