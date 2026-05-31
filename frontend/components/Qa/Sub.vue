<script setup lang="ts">
import type { FormInstance, FormRules } from 'element-plus'

const props = defineProps<{
  modelValue: boolean
}>()

const $emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'sub', value: {
    push_interval: string
    push_time: string
    end_time: string
    email: string }
  ): void
}>()

const { modelValue } = toRefs(props)

interface FormData {
  push_interval?: number
  push_time?: string
  end_time?: string
  email: string
}

const ruleFormRef = ref<FormInstance>()
const formData = reactive<FormData>({
  push_interval: undefined,
  push_time: undefined,
  end_time: undefined,
  email: '',
})

const rules = reactive<FormRules<FormData>>({
  push_interval: [
    { required: true, message: '请输入推送频率', trigger: 'blur' },
  ],
  push_time: [
    { required: true, message: '请输入推送时间', trigger: 'blur' },
  ],
  end_time: [
    { required: true, message: '请输入结束时间', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱', trigger: 'blur' },
  ],
})

async function submitForm(formEl: FormInstance | undefined) {
  if (!formEl)
    return
  await formEl.validate((valid, fields) => {
    if (valid) {
      const data = {
        push_interval: `${formData.push_interval!}`,
        push_time: formData.push_time!,
        end_time: formData.end_time!,
        email: formData.email!,
      }
      $emit('sub', data)
      resetForm()
      $emit('update:modelValue', false)
    }
  })
}

function resetForm() {
  formData.push_interval = undefined
  formData.push_time = undefined
  formData.end_time = undefined
  formData.email = ''
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

function disableTime() {
  return []
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
        订阅最新进展
      </div>
    </template>
    <div class="px-[4px]">
      <div class="h-[46px] flex items-center mb-[20px]">
        <div
          class="w-[88px] h-[46px] flex items-center justify-center text-[#4044ED] text-[14px] leading-[22px] border-b border-b-[2px] border-[#4044ED]"
        >
          定时推送
        </div>
        <div class="h-[46px] px-[18px] flex items-center justify-center text-[rgba(0,0,0,0.26)] text-[14px] leading-[22px] ">
          主动推送（努力开发中～）
        </div>
      </div>
      <el-form
        ref="ruleFormRef"
        :model="formData"
        :rules="rules"
      >
        <div class="mb-[12px] text-[14px] leading-[22px] text-[rgba(0,0,0,0.9)]] required">
          推送频率
        </div>
        <div class="flex">
          <el-form-item prop="push_interval">
            <el-input-number v-model="formData.push_interval" :max="100" :min="1">
              <template #decrease-icon>
                <span class="text-[14px] leading-[22px] text-[rgba(0,0,0,0.9)]]">每</span>
              </template>
              <template #increase-icon>
                <span class="text-[14px] leading-[22px] text-[rgba(0,0,0,0.9)]]">天</span>
              </template>
            </el-input-number>
          </el-form-item>
          <el-form-item class="ml-[8px]" prop="push_time">
            <div class="m-input">
              <el-time-select
                v-model="formData.push_time"
                class="!w-[402px]"
                format="HH:mm"
                start="00:00"
                step="01:00"
                end="23:00"
                placeholder="请选择时间"
                :clearable="false"
              />
              <!-- <div class="i-ll-time text-[14px] absolute top-[9px] right-[9px] !text-[rgba(0,0,0,0.4)]" /> -->
            </div>
          </el-form-item>
        </div>
        <div class="mb-[12px] text-[14px] leading-[22px] text-[rgba(0,0,0,0.9)] required">
          结束日期
        </div>
        <el-form-item props="end_time">
          <div class="m-input">
            <el-date-picker v-model="formData.end_time" class="!w-[560px]" prefix-icon="Date" value-format="MM/DD/YYYY" placeholder="请选择时间" />
            <div class="i-ll-calendar text-[18px] absolute top-[9px] right-[7px] text-[rgba(0,0,0,0.4)]]" />
          </div>
        </el-form-item>
        <div class="mb-[12px] text-[14px] leading-[22px] text-[rgba(0,0,0,0.9)] required">
          邮箱
        </div>
        <el-form-item prop="email">
          <el-input v-model="formData.email" placeholder="请输入邮箱" />
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
