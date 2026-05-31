<script setup lang="ts">
const $emits = defineEmits<{
  (e: 'stop'): void
}>()
</script>

<template>
  <div
    class="qa-stop-btn"
    @click="$emits('stop')"
  >
    <div class="flex items-center">
      <div class="i-ll-stop text-[18px] text-[rgba(0,0,0,0.9)]" />
      <span class="ml-[12px] text-[16px] text-[rgba(0,0,0,0.9)] leading-[24px] font-normal">停止生成</span>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.qa-stop-btn {
    cursor: pointer;
    border: 1px solid #DCDCDC;
    height: 48px;
    border-radius: 30px;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 8px 32px;
    background: #FFFFFF;
    box-shadow: 0px 1px 2px 0px rgba(0, 0, 0, 0.03),0px 1px 6px -1px rgba(0, 0, 0, 0.02),0px 2px 4px 0px rgba(0, 0, 0, 0.02);
}
</style>
