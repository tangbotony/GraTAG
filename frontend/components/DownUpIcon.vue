<script setup lang="ts">
import stats from '~/lib/stats'

const $emit = defineEmits<{
  (e: 'change', value: boolean): void
}>()

const up = ref(false)
const down = ref(false)

watch(up, (val) => {
  if (val) {
    down.value = false
    $emit('change', true)
    stats.track('qa', {
      action: !val ? 'dislike' : 'like',
    })
  }
})

watch(down, (val) => {
  if (val) {
    up.value = false
    $emit('change', false)
    stats.track('qa', {
      action: !val ? 'dislike' : 'like',
    })
  }
})
</script>

<template>
  <div class="flex items-center">
    <div
      class="cursor-pointer hover:text-[#4044ED]"
      :class="{
        'i-ll-up-line': !up,
        'i-ll-up-fill': up,
        'text-[#8B9096]': !up,
        'text-[#4044ED]': up,
      }"
      @click="up = !up"
    />
    <div class="ml-[15px]" />
    <div
      class="cursor-pointer rotate-180 hover:text-[#4044ED]"
      :class="{
        'i-ll-up-line': !down,
        'i-ll-up-fill': down,
        'text-[#8B9096]': !down,
        'text-[#4044ED]': down,
      }"
      @click="down = !down"
    />
  </div>
</template>
