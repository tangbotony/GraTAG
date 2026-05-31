<script setup lang="ts">
import stats from '~/lib/stats'
import type { ProContinueDataType } from '~/composables/ai/useWriting'

const props = defineProps<{
  type: string
  text: string
  proContinueData?: ProContinueDataType
  selected_content: string
  context_above: string
  context_below: string
  polish_type?: string
}>()

const emits = defineEmits<{
  (e: 'change', value: string): void
}>()

function handleDownUp(value: boolean) {
  if (value)
    emits('change', 'like')

  else
    emits('change', 'dislike')

  const proContinueData = props.type === 'continue_profession' ? props.proContinueData : {}
  const polishType = props.polish_type ? { polish_type: props.polish_type } : {}
  stats.track(`text-${props.type}`, {
    action: !value ? 'dislike' : 'like',
    text: props.text || '',
    selected_content: props.selected_content,
    context_above: props.context_above,
    context_below: props.context_below,
    ...toRaw(proContinueData),
    ...polishType,
  })
}
</script>

<template>
  <DownUpIcon @change="handleDownUp" />
</template>
lib/stats
