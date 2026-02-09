<script setup lang="ts">
const props = defineProps<{
  duration?: number
  width?: number
  textColor?: string
  disableCancel?: boolean
  hiddeText?: boolean
}>()

const $emits = defineEmits<{
  (e: 'cancle'): void
}>()

const second = ref(0)
let cancel: () => void | undefined
onMounted(() => {
  if (props.duration) {
    cancel = countdown((val) => {
      second.value = val
    }, props.duration)
  }
})

function handleCancel() {
  cancel?.()
  $emits('cancle')
}

onUnmounted(() => {
  cancel?.()
})
</script>

<template>
  <div class="flex flex-col items-center">
    <div
      :style="{
        width: props.width ? `${props.width}px` : '40px',
        height: props.width ? `${props.width}px` : '40px',
      }"
    >
      <img
        class="w-full h-full"
        src="~/assets/images/generate/generate-loading.png"
      >
    </div>

    <div
      v-if="!props.hiddeText"
      class="mt-[12px] mb-[15px] text3 cursor-pointer" :style="{
        color: textColor || '#8B9096',
      }"
    >
      <template v-if="props.duration && props.duration > 0">
        预计还需{{ second }}秒 <span v-if="!props.disableCancel" @click="handleCancel">…⚠︎取消</span>
      </template>
      <template v-else>
        AI生成中… <span v-if="!props.disableCancel" @click="handleCancel">⚠︎取消</span>
      </template>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.text3 {
  text-align: center;
  font-size: 10px;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
}
</style>
