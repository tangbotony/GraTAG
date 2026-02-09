<script setup lang="ts">
import type { FormInstance, FormRules } from 'element-plus'

const props = defineProps<{
  modelValue: boolean
  answer: string
}>()

const $emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const { modelValue } = toRefs(props)

interface FormData {
  type: string
  title: string
  thesis: string
}

const ruleFormRef = ref<FormInstance>()
const formData = reactive<FormData>({
  type: 'xinhua',
  title: '',
  thesis: '',
})

const rules = reactive<FormRules<FormData>>({
  type: [
    { required: true, message: '请选择类型', trigger: 'blur' },
  ],
})

const router = useRouter()

async function submitForm(formEl: FormInstance | undefined) {
  if (!formEl)
    return
  await formEl.validate((valid, fields) => {
    if (valid) {
      const data = {
        type: formData.type,
        title: formData.title,
        thesis: formData.thesis,
        answer: props.answer,
      }

      useSessionStorage('qa-temp-gen-new', data)
      createFile()
    }
  })
}

async function createFile() {
  const { error, data } = await useFileCreate({
    name: '',
    parent_id: '-1',
    text: '',
    plain_text: '',
  })
  if (!error.value && data.value?.doc_id)
    navigateTo(`/document/${data.value.doc_id}`)
}

function resetForm() {
  formData.type = 'xinhua'
  formData.title = ''
  formData.thesis = ''
}

function cancel() {
  resetForm()
  $emit('update:modelValue', false)
}

function ok() {
  submitForm(ruleFormRef.value)
}

function handleModel(event: boolean) {
  $emit('update:modelValue', event)
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="600"
    @update:model-value="handleModel"
    @before-close="resetForm"
  >
    <template #header>
      <div class="text-[16px] font-600 leading-[24px] text-[rgba(0,0,0,0.9)]]">
        一键生成文章
      </div>
    </template>
    <div class="px-[4px]">
      <el-form
        ref="ruleFormRef"
        :model="formData"
        :rules="rules"
      >
        <div class="mb-[12px] mt-[20px] text-[14px] leading-[22px] text-[rgba(0,0,0,0.9)] required">
          稿件类型
        </div>
        <el-form-item props="type">
          <el-select v-model="formData.type" class="!w-[560px]">
            <el-option label="评论文章" value="xinhua" />
          </el-select>
        </el-form-item>
        <div class="mb-[12px] text-[14px] leading-[22px] text-[rgba(0,0,0,0.9)]">
          参考标题
        </div>
        <el-form-item props="title">
          <el-input v-model="formData.title" class="!w-[560px]" placeholder="请输入参考标题" />
        </el-form-item>
        <div class="mb-[12px] text-[14px] leading-[22px] text-[rgba(0,0,0,0.9)]">
          参考论点
        </div>
        <el-form-item prop="thesis" class="!mb-[62px]">
          <el-input v-model="formData.thesis" placeholder="请输入参考论点" />
        </el-form-item>
      </el-form>
    </div>
    <template #footer>
      <div class="dialog-footer">
        <el-button class="!bg-[#E7E7E7] ml-[12px] mr-[8px] !border-none" round @click.stop="cancel">
          <span class="text-[14px] leading-[22px] font-normal text-[rgba(0,0,0,0.9)]">取消</span>
        </el-button>
        <el-button class="!mx-0" type="primary" round @click="ok">
          <span class="text-[14px] leading-[22px] font-normal">确认</span>
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
.m-input {
    position: relative;
}
.m-input:deep(.el-input__prefix) {
    display: none;
}

.m-input:deep(.el-input__wrapper) {
    padding-right: 33px;
}
</style>
