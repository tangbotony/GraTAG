<script setup lang="ts">
const props = defineProps<{
  id: string
}>()

async function deleteArticle() {
  useFileDelete(props.id)
  navigateTo('/file')
}
</script>

<template>
  <el-popconfirm
    width="236"
    title="确定移入废纸篓?"
    confirm-button-text="确定"
    cancel-button-text="取消"
    @confirm="deleteArticle"
  >
    <template #reference>
      <div class="i-ll-edit-delete cursor-pointer text-[16px] text-gray-lighter-color ml-[24px]" />
    </template>
  </el-popconfirm>
</template>
