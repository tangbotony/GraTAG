<script setup lang="ts">
import type { FormInstance } from 'element-plus'

const props = defineProps<{
  step: number
}>()

const $emits = defineEmits<{
  (e: 'update:step', value: number): void
  (e: 'submit', value: FormDataType): void
}>()

const formData = reactive({
  direction: [
    { value: '', type: 'aspect', title: '续写领域', key: 0, placeholder: '文章领域，如时政、财经、体育、科技等' },
  ],
  demand: '',
  style: '书面化',
  length: '2',
})

const directionData = ref([
  { value: 'aspect', title: '续写领域', placeholder: '文章领域，如时政、财经、体育、科技等' },
  { value: 'keywords', title: '续写关键词', placeholder: '文章事件要素，如“防沙治沙“”亚运会“等' },
  { value: 'direction', title: '续写方向', placeholder: '事件的原因、影响、措施等，如“防沙治沙的措施”' },
  { value: 'orientation', title: '续写定位', placeholder: '如使用概述或引用，论点或论据等来表现' },
])

export interface FormDataType {
  direction: {
    type: string
    value: string
    key: number
  }[]
  demand?: string
  style: string
  length: string
}

const formRef = ref<FormInstance>()
let key = 0

function handleDirection(val: string, title: string, placeholder: string) {
  const findIndex = formData.direction.findIndex(item => item.type === val)
  if (findIndex === -1)
    formData.direction.push({ value: '', type: val, title, key: ++key, placeholder })

  else
    formData.direction.splice(findIndex, 1)
}

function submit() {
  formRef.value?.validate(async (valid) => {
    if (!valid)
      return
    $emits('update:step', 2)
    $emits('submit', formData)
  })
}

function validateNoMore500(rule: any, value: any, callback: any) {
  if (value.length > 500)
    callback(new Error('不能超过500字'))

  else
    callback()
}

const isDisableButton = computed(() => {
  return formData.direction.map(item => item.value).join('').trim().length === 0
})
</script>

<template>
  <div class="container">
    <div class="relative mt-[32px] mb-[24px]">
      <el-steps :active="props.step" align-center>
        <el-step>
          <template #title>
            <div>
              填写续写偏好
            </div>
          </template>
        </el-step>

        <el-step>
          <template #title>
            <div>生成续写结果</div>
          </template>
        </el-step>
      </el-steps>
      <div class="absolute top-0 left-0 right-0 bottom-0 flex justify-around items-center z-10">
        <div class="w-[120px] h-full cursor-pointer" @click="$emits('update:step', 1)" />
        <div class="w-[120px] h-full" />
      </div>
    </div>
    <el-form v-show="step === 1" ref="formRef" :model="formData">
      <p class="mb-[8px]">
        续写方向
      </p>

      <div class="no-border w-full box-border p-[12px]">
        <div class="flex items-center mb-[8px]">
          <div
            v-for="item in directionData"
            :key="item.value"
            class="direction-tag cursor-pointer"
            :class="{
              'is-active': formData.direction.findIndex(d => d.type === item.value) !== -1,
            }"
            @click="handleDirection(item.value, item.title, item.placeholder)"
          >
            {{ item.title }}
          </div>
        </div>
        <el-form-item
          v-for="(d, index) in formData.direction"
          :key="d.key"
          :prop="`direction.${index}.value`"
        >
          <div class="flex items-start w-full">
            <div class="inline-block basis-auto">
              {{ d.title }}:
            </div>
            <el-input v-model="d.value" class="flex-1" :placeholder="d.placeholder" type="textarea" autosize />
          </div>
        </el-form-item>
      </div>

      <p class="mb-[8px] mt-[24px]">
        特殊要求
      </p>
      <el-form-item
        label=""
        prop="demand"
        :rules="{
          validator: validateNoMore500,
          trigger: 'blur',
        }"
      >
        <el-input v-model="formData.demand" placeholder="输入需要重点参照的背景知识、数据等信息" :rows="4" type="textarea" />
      </el-form-item>
      <p class="mb-[8px] mt-[24px]">
        语言风格
      </p>
      <el-form-item label="" prop="style" :rules="{ required: true, message: '请选择语言风格', trigger: 'blur' }">
        <el-radio-group v-model="formData.style">
          <el-radio value="书面化" label="书面化">
            书面风格
          </el-radio>
          <el-radio value="口语化" label="口语化">
            口语风格
          </el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="" prop="length" :rules="{ required: true, message: '请选择续写长度', trigger: 'blur' }">
        <el-radio-group v-model="formData.length">
          <el-radio value="2" label="2">
            中
          </el-radio>
          <el-radio value="1" label="1">
            短
          </el-radio>
          <el-radio value="4" label="4">
            长
          </el-radio>
        </el-radio-group>
      </el-form-item>
      <el-button :disabled="isDisableButton" class="base-btn mb-[46px] mt-[24px]" @click="submit">
        下一步：生成续写结果
      </el-button>
    </el-form>
  </div>
</template>

<style lang="scss" scoped>
.container {
  &:deep(.el-step__head.is-finish  ) {
    color: var(--c-text-normal) !important;
    border-color: var(--c-text-normal) !important;
  }

  &:deep(.el-step__title.is-finish) {
    color: var(--c-text-normal) !important;
  }

  &:deep(.el-step__title, .el_step__head) {
    color: var(--c-text-gray-lighter) !important;
    border-color: var(--c-text-gray-lighter) !important;
    font-size: 14px !important;
    font-style: normal !important;
    font-weight: 400 !important;
    line-height: 22px !important;
  }

  &:deep(.el-step__head.is-process) {
    color: var(--c-text-gray-lighter) !important;
    border-color: var(--c-text-gray-lighter) !important;
  }
}

.no-border {
  border-radius: 8px;
  border: 1px solid var(--neutral-5, #D9D9D9);
  margin-bottom: 8px;
}

.no-border:deep(.el-textarea) {
  --el-input-border-color: transparent !important;

  --el-input-focus-border-color: transparent !important;
  --el-input-hover-border-color: transparent !important;
  resize: none;
}

.no-border:deep(.el-form-item) {
  margin-bottom: 8px;
}
p {
  color: var(--c-text-color, rgba(0, 0, 0, 0.85));
  font-size: 14px;
  font-style: normal;
  font-weight: 400;
  line-height: 22px; /* 157.143% */
}

.direction-tag {
  border-radius: 12px;
  border: 1px dashed  #D9D9D9;
  padding: 0px 12px;
  margin-right: 8px;
  font-size: 14px;
  font-style: normal;
  font-weight: 400;
  line-height: 22px;
  color: var(--c-text-color);

  &:hover {
    border: 1px dashed #4044ED;
    color: #4044ED;
  }

  &.is-active {
    color: #4044ED;
    border: 1px solid #4044ED;
    background: #E5E6FF;
  }
}
</style>
