<script lang="ts" setup>
const props = defineProps<{
  percentage: number
  showText: boolean
}>()
</script>

<template>
  <el-progress
    v-bind="{ ...props, ...$attrs }"
    class="m-progress"
  >
    <slot />
  </el-progress>
</template>

<style>
.m-progress {
  .el-progress-bar__outer {
    background-color: #E5E6FF !important;
  }
}
</style>
