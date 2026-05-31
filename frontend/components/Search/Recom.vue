<script setup lang="ts">
const props = defineProps<{
  data: string[]
}>()
const $emit = defineEmits<{
  (e: 'select', value: string): void
}>()

function handleSelect(value: string) {
  $emit('select', value)
}
</script>

<template>
  <div class="w-[700px] flex flex-wrap justify-center gap-[16px] mt-[32px]">
    <div
      v-for="(item, index) in props.data"
      :key="`${item}-${index}`"
      class="px-[16px] py-[6px] rounded-[20px] border border-[#D9D9D9] text-[#666666] text-[14px] leading-normal font-normal hover:border-[#4044ED] hover:text-[#4044ED] cursor-pointer"
      @click="handleSelect(item)"
    >
      {{ item }}
    </div>
  </div>
</template>
