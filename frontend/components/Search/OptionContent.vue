<script setup lang="ts">
const props = defineProps<{
  value: string
  diffValue: string
}>()

const html = computed(() => {
  const index = props.value.indexOf(props.diffValue)
  if (index === -1)
    return props.value
  else
    return `${props.value.slice(0, index)}<span style="color: #4044ED;">${props.diffValue}</span>${props.value.slice(index + props.diffValue.length)}`
})
</script>

<template>
  <div class="w-[648px] truncate" v-html="html" />
</template>
