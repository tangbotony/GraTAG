<script setup lang="ts">
const props = defineProps<{
  placeholder?: string
  modelValue: string
  maxlength?: number
}>()

const emit = defineEmits<{
  (e: 'update:model-value', value: string): void
  (e: 'focus'): void
  (e: 'blur'): void
  (e: 'input', value: string): void
}>()

const isFocus = ref(false)
const isInput = ref(false)
const isHover = ref(false)

function handleInput(value: string) {
  emit('update:model-value', value)
  emit('input', value)
  isInput.value = true
}

function handleFocus() {
  isFocus.value = true
  emit('focus')
}

function handleBlur() {
  isFocus.value = false
  isInput.value = false
  emit('blur')
}
</script>

<template>
  <div
    class="relative w-full input-container"
    :class="{
      hover: isHover,
    }"
    @mouseover="isHover = true"
    @mouseleave="isHover = false"
  >
    <div v-if="!isFocus && props.modelValue.length === 0" class="absolute top-0 left-0 bottom-o right-0 text3 z-10 truncate px-[12px] pt-[5px] pointer-events-none">
      {{ placeholder }}
    </div>
    <el-input
      :model-value="props.modelValue"
      size="small"
      style="width: 100%;"
      :maxlength="props.maxlength"
      @focus="handleFocus"
      @input="handleInput"
      @blur="handleBlur"
    />
    <div v-if="isInput" class="absolute text1 right-[9px] top-[5px]">
      <span
        :class="{
          'text-[#4044ED]': props.modelValue.length < 100,
          'text-[#EC1D13]': props.modelValue.length === 100,
        }"
      >{{ props.modelValue.length }}</span>
      <span>/{{ maxlength }}</span>
    </div>
    <slot :hover="isHover" :input="isInput" :focus="isFocus" />
  </div>
</template>

<style lang="scss" scoped>
.text1 {
    color: var(--N1, #19222E);
    font-size: 12px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px; /* 157.143% */
}
.text3 {
  color: rgb(216, 216, 216);
  font-size: 12px;
  font-weight: 350;
  line-height: 22px;
}

.hover:deep(.el-input__wrapper) {
    background-color: #F5F5F6 !important;
}

.input-container {
  &:deep( .el-input__wrapper) {
    padding: 5px 12px !important;
    border-radius: 2px !important;
  }
}
</style>
