<script setup lang="ts">
const props = defineProps<{
  text: string
  searchText: string
}>()

const pos = props.text.indexOf(props.searchText)

function render() {
  if (pos === -1)
    return h('span', { class: 'text-search text-unmatched' }, props.text)

  return [
    h('span', { class: 'text-unmatched' }, props.text.slice(0, pos)),
    h('span', { class: 'text-matched' }, props.text.slice(pos, pos + props.searchText.length)),
    h('span', { class: 'text-unmatched' }, props.text.slice(pos + props.searchText.length)),
  ]
}
</script>

<template>
  <span class="text-search">
    <render />
  </span>
</template>

<style lang="scss" scoped>
    .text-search {
      font-size: 14px;
      font-style: normal;
      font-weight: 500;
      line-height: 22px; /* 157.143% */

      &:deep( .text-matched ) {
          color: var(--c-text-normal);
      }

      &:deep( .text-unmatched ) {
          color: var(--c-text-black);
      }
    }
</style>
