<script setup lang="ts">
const props = defineProps<{
  progress: string
  data: QaAdditionQuery
}>()
const $emits = defineEmits<{
  (e: 'next'): void
}>()
const { progress, data } = toRefs(props)
const isBig = computed(() => {
  let count = 0
  data.value.options.forEach((i) => {
    count += i.length
  })
  if (count > 20)
    return true

  return false
})

function handleCheckBoxChange(val: boolean, op: string) {
  if (val)
    data.value.selected_option.push(op)
  else
    data.value.selected_option = data.value.selected_option.filter(i => i !== op)
}

const isTextError = ref(false)
function handleOtherOptionChange(val: string) {
  if (val.length > 100)
    isTextError.value = true
  else
    isTextError.value = false
  data.value.other_option = val
}

function handlePass() {
  data.value.selected_option = []
  if (isTextError.value) {
    data.value.other_option = ''
    isTextError.value = false
  }
  $emits('next')
}
function handleSend() {
  if (isTextError.value)
    return

  if (data.value.other_option && data.value.other_option.trim().length > 0)
    data.value.selected_option.push(data.value.other_option)

  $emits('next')
}
</script>

<template>
  <div>
    <div
      class="w-[700px] rounded-[12px] bg-[#FFFFFF] border border-solid border-[#EEE] p-[24px] max-h-min mb-[56px]"
    >
      <div class="flex items-center mb-[20px]">
        <div class="i-ll-magic text-[16px] text-normal-color mr-[6px]" />
        <span class="text-[16px] font-normal leading-normal text-[rgba(0,0,0,0.9)]">补充以下内容，可获得更精确的回答</span>
      </div>
      <div class="text-[14px] font-normal leading-[22px] text-[rgba(0,0,0,0.6)] mb-[12px]">
        {{ data.title }}
      </div>
      <template v-if="!isBig">
        <el-checkbox-group v-model="data.selected_option">
          <el-checkbox
            v-for="op in data.options"
            :key="op"
            :label="op"
            :value="op"
          />
        </el-checkbox-group>
      </template>
      <template v-else>
        <div class="w-full mb-[24px]">
          <div
            v-for="op in data.options"
            :key="op"
            class="flex items-start mb-[12px]"
          >
            <el-checkbox
              class="!h-[24px]"
              :checked="data.selected_option.includes(op)"
              @change="handleCheckBoxChange($event as boolean, op)"
            />
            <div class="ml-[8px] text-[14px] font-normal leading-[22px] text-[rgba(0,0,0,0.9)]">
              {{ op }}
            </div>
          </div>
        </div>
      </template>
      <div class="text-[14px] pt-[15px] flex items-center font-normal leading-[22px] text-[rgba(0,0,0,0.6)] mb-[12px]">
        <span class="ml-[8px]">其他内容</span>
      </div>
      <div class="relative w-[652px] mb-[24px] c-textarea">
        <el-input
          :model-value="data.other_option"
          autosize
          type="textarea"
          placeholder="请输入内容"
          @update:model-value="handleOtherOptionChange"
        />
        <div class="text-[14px] font-noraml leading-22px absolute bottom-[5px] right-[12px] text-[rgba(0,0,0,0.4)]">
          {{ data.other_option.length }}/100
        </div>
        <div v-if="isTextError" class="text-[#D54941] absolute bottom-[-20px] text-[12px] leading-[20px] font-normal">
          内容不能超过100字，请删减字数
        </div>
      </div>
      <div class="flex items-center justify-end">
        <el-button class="!bg-[#E7E7E7] mr-[8px]" round @click="handlePass">
          <span class="text-[14px] text-[rgba(0,0,0,0.9)] leading-[22px] font-normal">跳过问题，生成答案</span>
        </el-button>
        <el-button class="!ml-0" type="primary" round @click="handleSend">
          <div class="flex items-center">
            <div class="i-ll-send-circle text-white mr-[8px]" />
            <span class="text-white text-[14px] leading-[22px] font-normal">确定</span>
          </div>
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.c-textarea:deep(.el-textarea__inner) {
  padding-right: 64px !important;
}
</style>
