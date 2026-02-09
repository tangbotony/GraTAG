<script setup lang="ts">
import { type HTMLAttributes } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps<{
  modelValue: boolean
  class?: HTMLAttributes['class']
  disabled: boolean
}>()

const $emits = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()
const { modelValue } = toRefs(props)

function handleClick() {
  if (props.disabled)
    return
  $emits('update:modelValue', !modelValue.value)
}
</script>

<template>
  <div
    v-bind="{ ...$attrs }"
    :class="cn('w-full rounded-[8px] p-[12px] bg-white border min-h-[47px] border-[#EEE] relative', props.class)"
  >
    <div v-if="!modelValue" class="w-full">
      <slot name="header" />
    </div>
    <div
      class="w-full overflow-hidden"
      :class="{
        'h-0': !modelValue,
        'h-auto': modelValue,
      }"
    >
      <slot />
    </div>
    <div v-if="!props.disabled" class="w-full h-[47px] cursor-pointer absolute top-0 left-0" @click="handleClick" />
    <div
      class="absolute top-[12px] right-[12px] text-[rgba(0,0,0,0.6)] cursor-pointer"
      @click="handleClick"
    >
      <div
        v-if="!props.disabled"
        class="i-ll-arrow-left text-[20px]"
        :class="{
          'rotate-90': modelValue,
          'rotate-270': !modelValue,
        }"
      />
    </div>
  </div>
</template>
