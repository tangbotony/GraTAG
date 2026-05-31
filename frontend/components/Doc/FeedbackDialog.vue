<script setup lang="ts">
import stats from '~/lib/stats'
import type { ProContinueDataType } from '~/composables/ai/useWriting'

const props = defineProps<{
  modelValue: boolean

  type: string
  text?: string
  proContinueData?: ProContinueDataType
  selected_content: string
  context_above: string
  context_below: string
  polish_type?: string
}>()
const $emits = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const ideal = ref('')
const isFact = ref(false)
const isValue = ref(false)
const isDiff = ref(false)

function ok() {
  if (ideal.value.trim().length === 0)
    return

  let desc = ideal.value.trim() ? `【反馈内容】：${ideal.value.trim()};` : ''
  desc += `${isFact.value ? '生成内容不符合事实;' : ''}${isValue.value ? '生成内容价值观不良;' : ''}${isDiff.value ? '生成内容和期望相差甚远;' : ''}\n`
  desc += `【功能】：${props.type};\n`
  desc += `【生成内容】：${props.text};\n`
  desc += `【选中内容】：${props.selected_content};\n`
  desc += `【上下文】：${props.context_above};${props.context_below};\n`
  if (props.polish_type)
    desc += `【润色类型】：${props.polish_type};\n`

  if (props.type === 'continue_profession' && props.proContinueData)
    desc += `【专业续写】：${JSON.stringify(props.proContinueData)};\n`
  useFeedback({
    description: desc,
    type: 'content',
  })

  const proContinueData = props.type === 'continue_profession' ? props.proContinueData : {}
  const polishType = props.polish_type ? { polish_type: props.polish_type } : {}
  stats.track(`text-${props.type}`, {
    action: 'feedback',
    text: props.text || '',
    selected_content: props.selected_content,
    context_above: props.context_above,
    context_below: props.context_below,
    feedback_text: ideal.value.trim(),
    feedback_is_fact: isFact.value,
    feedback_is_bad: isValue.value,
    feedbaack_is_expected: isDiff.value,
    ...toRaw(proContinueData),
    ...polishType,
  })

  $emits('update:modelValue', false)
  ElMessage.success('感谢您的反馈')
}

watch(() => props.modelValue, (val) => {
  if (!val) {
    ideal.value = ''
    isFact.value = false
    isValue.value = false
    isDiff.value = false
  }
})

const isDisabled = computed(() => {
  if (ideal.value.trim().length === 0)
    return true

  if (isFact.value || isValue.value || isDiff.value || ideal.value.trim().length > 0)
    return false

  return true
})
</script>

<template>
  <el-dialog
    :model-value="props.modelValue"
    title="感谢您的反馈，期待您更进一步的建议"
    width="512"
    append-to-body
    @update:model-value="$emits('update:modelValue', $event)"
  >
    <div class="flex flex-col items-start w-full">
      <el-input
        v-model="ideal"
        :autosize="{ minRows: 2 }"
        type="textarea"
        placeholder="请在这里留下您宝贵的意见"
      />
      <el-checkbox v-model="isFact" class="mt-[8px]" size="small" label="生成内容不符合事实" />
      <el-checkbox v-model="isValue" size="small" label="生成内容价值观不良" />
      <el-checkbox v-model="isDiff" size="small" label="生成内容和期望相差甚远" />
    </div>
    <template #footer>
      <div class="flex justify-end w-full">
        <el-button type="primary" :disabled="isDisabled" @click="ok">
          提交反馈意见
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>
