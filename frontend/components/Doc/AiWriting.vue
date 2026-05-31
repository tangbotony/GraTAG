<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'
import { NEWS_KIND } from '~/consts/editor'

const props = defineProps<{
  editor: Editor
  scrollContainer: any
}>()
const $emits = defineEmits<{
  (e: 'closed'): void
  (e: 'show'): void
  (e: 'hide'): void
}>()
// const DocGenerateAsync = defineAsyncComponent(() => import('~/components/Doc/Generate/index.vue'))
// const DocNewsAsync = defineAsyncComponent(() => import('~/components/Doc/News/index.vue'))

const manuscriptVal = ref('')
const initManuscriptVal = ref('')
const sessionId = getRandomString()
const step = ref(0)
function manuscriptChange(val: string) {
  manuscriptVal.value = val
  step.value = 1
}
function handleAiClose() {
  $emits('closed')
}
function handleAiHide() {
  $emits('hide')
}
function handleAiShow() {
  $emits('show')
}
function back() {
  initManuscriptVal.value = manuscriptVal.value
  step.value = 0
}

// onBeforeMount(async () => {
//   const c1 = () => import('~/components/Doc/Generate/index.vue')
//   const c2 = () => import('~/components/Doc/News/index.vue')
//   await Promise.all([c1(), c2()])
// })

defineExpose({
  init: async () => {
  },
  clear: () => {
  },
})

onMounted(async () => {
  const data = sessionStorage.getItem('qa-temp-gen-new')
  if (data)
    manuscriptChange(NEWS_KIND.Review)
})
</script>

<template>
  <div class="h-full aigenerte">
    <DocAiWritingKind
      v-if="step === 0"
      :init-type="initManuscriptVal"
      @closed="handleAiClose"
      @next-txt="manuscriptChange"
    />
    <div v-show="step === 1" class="h-full aigenerte">
      <template v-if="(manuscriptVal === 'review')">
        <DocGenerate
          :editor="props.editor"
          :scroll-container="props.scrollContainer"
          @back="back"
          @hide="handleAiHide"
          @show="handleAiShow"
          @closed="handleAiClose"
        />
      </template>
      <template v-else>
        <DocNews
          :key="manuscriptVal"
          :editor="props.editor"
          :scroll-container="props.scrollContainer"
          :session-id="sessionId"
          :type="manuscriptVal"
          @back="back"
          @hide="handleAiHide"
          @show="handleAiShow"
          @closed="handleAiClose"
        />
      </template>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.aigenerte{
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
</style>
