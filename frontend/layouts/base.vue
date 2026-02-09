<script setup lang="ts">
const route = useRoute()
const isPadding = computed(() => (route.path !== '/search' && route.name !== 'qa-id' && route.name !== 'qa'))
const className = computed(() => {
  if (route.name === 'qa-id')
    return 'min-w-[1240px] flex-1 bg-[#F0F2F5] h-full'
  return 'flex-1 min-w-[1072px] bg-[#F0F2F5] h-full'
})
</script>

<template>
  <div class="flex h-full w-full">
    <Aside />
    <main id="right-main" :class="className">
      <div
        class="w-full h-full box-border bg-white rounded-l-[24px] overflow-hidden"
        :class="{
          'px-[24px]': isPadding,
          'py-[24px]': isPadding,
        }"
      >
        <slot />
      </div>
    </main>
  </div>
</template>
