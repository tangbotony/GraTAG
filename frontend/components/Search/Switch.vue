<script setup lang="ts">
const mode = defineModel<boolean>()
</script>

<template>
  <div class="my-switch">
    <el-switch
      v-model="mode"
      inline-prompt
      active-text="Pro"
      inactive-text="Pro"
    />
  </div>
</template>

<style lang="scss" scoped>
.my-switch {
    &:deep(.el-switch__core) {
        width: 48px;
        height: 22px;
        border-radius: 12px;
        background: #F1F1F1;
        border: none;
    }
    &:deep(.el-switch__action) {
        width: 12px;
        height: 12px;
        box-shadow: 0px 1px 10px 0px rgba(0, 0, 0, 0.05),0px 4px 5px 0px rgba(0, 0, 0, 0.08),0px 2px 4px -1px rgba(0, 0, 0, 0.12);
        left: 6px;
    }

    &:deep(.el-switch__inner .is-text) {
        font-size: 12px;
        font-weight: normal;
        line-height: 20px;
        color: #666666;
    }

    &:deep(.is-checked .el-switch__core) {
        background: #4044ED;
    }

    &:deep(.is-checked .el-switch__inner .is-text) {
        color: white;
    }

    &:deep(.el-switch) {
      height: 22px;
    }
}
</style>
