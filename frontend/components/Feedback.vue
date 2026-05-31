<script setup lang="ts">
import type { UploadFile } from 'element-plus/es/components/upload/index'

const dialogVisible = ref(false)
const desc = ref('')
const idea = ref('')
const contact = ref('')

const isOk = computed(() => {
  if (desc.value || idea.value)
    return true

  return false
})

const fileList = ref<UploadFile[]>([])

const isloading = ref(false)

watch(fileList, (val) => {
  isloading.value = true
  fileList.value.forEach(async (f) => {
    if (f.url?.startsWith('blob:') && f.raw) {
      const { data, error } = await useImageUpload(f.raw)
      if (!error.value && data.value?.image_url)
        f.url = data.value.image_url
    }
  })
  isloading.value = false
})

function handlePictureCardPreview(file: UploadFile) {
  window.open(file.url)
}

watch(dialogVisible, (val) => {
  if (!val) {
    desc.value = ''
    idea.value = ''
    contact.value = ''
    fileList.value = []
  }
})

const isFeedbackloading = ref(false)
async function submit() {
  isFeedbackloading.value = true
  const { data, error } = await useFeedback({
    pic_list: fileList.value.map(f => f.url).filter(i => !!i) as string[],
    brief: desc.value,
    description: idea.value,
    contact: contact.value,
    type: 'function',
  })
  isFeedbackloading.value = false
  if (!error.value) {
    dialogVisible.value = false
    ElMessage.success('感谢您的反馈')
  }
}
</script>

<template>
  <div class="px-[12px] py-[8px] flex items-center cursor-pointer" @click="dialogVisible = true">
    <div class="i-ll-feedback text-[16px] mr-[4px]" />
    <span class="text-[16px]">问题反馈</span>
  </div>
  <el-dialog
    v-model="dialogVisible"
    title="反馈"
    :width="512"
    append-to-body
  >
    <div class="container py-[30px]">
      <p class="title">
        简要描述
      </p>
      <el-input
        v-model="desc"
        type="text"
        placeholder="简要描述"
      />
      <p class="title">
        详情意见
      </p>
      <el-input
        v-model="idea"
        :rows="3"
        type="textarea"
        placeholder="详情意见"
      />
      <p class="title">
        联系方式
      </p>
      <el-input
        v-model="contact"
        type="text"
        placeholder="联系方式"
      />
      <p class="title">
        问题截图
      </p>
      <div
        v-loading="isloading"
      >
        <el-upload
          v-model:file-list="fileList"
          list-type="picture-card"
          :on-preview="handlePictureCardPreview"
          :auto-upload="false"
        >
          <div class="i-ll-plus text-[40px] text-[#D9D9D9]" />
        </el-upload>
      </div>
    </div>
    <template #footer>
      <el-button type="primary" :disabled="!isOk" :loading="isFeedbackloading" @click="submit">
        提交反馈
      </el-button>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
.title {
  color: var(--c-text-black, rgba(0, 0, 0, 0.85));
  text-align: left;
  font-size: 14px;
  font-style: normal;
  font-weight: 400;
  line-height: 22px; /* 157.143% */
  margin-bottom: 8px;
}

.container {
  &:deep(.el-input) {
    margin-bottom: 16px;
  }

  &:deep(.el-textarea) {
    margin-bottom: 16px;
  }
}
</style>
