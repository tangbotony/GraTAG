<script setup lang="ts">
const props = defineProps<{
  modelValue: boolean
}>()

const $emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    direction="ltr"
    class="!w-[400px]"
    @update:model-value="$emit('update:modelValue', !modelValue)"
  >
    <template #header>
      <div class="flex items-center">
        <span class="text-[16px] font-500 leading-[24px] text-[rgba(0,0,0,0.9)]">历史记录</span>
      </div>
    </template>
    <template #default>
      <div class="px-[16px] py-[24px] h-[calc(100vh-48px)] w-full overflow-y-scroll">
        <SearchHistory v-if="modelValue" />
      </div>
    </template>
  </el-drawer>
</template>
