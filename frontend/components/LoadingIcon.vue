<script setup lang="ts">
const props = defineProps<{
  width: number
}>()
const { width } = toRefs(props)
</script>

<template>
  <span :style="{ width: `${width}px`, height: `${width}px` }" class="loader" />
</template>

<style scoped>
.loader {
  border: 2px solid #4044ED;
  border-bottom-color: transparent;
  border-radius: 50%;
  display: inline-block;
  box-sizing: border-box;
  animation: rotation 1s linear infinite;
  }

  @keyframes rotation {
  0% {
      transform: rotate(0deg);
  }
  100% {
      transform: rotate(360deg);
  }
}
</style>
