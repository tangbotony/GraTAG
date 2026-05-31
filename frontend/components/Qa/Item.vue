<script setup lang="ts">
import type { QaCollectionState } from '~/store/qa'
import { QaMode, QaProgressState, useQaStore } from '~/store/qa'

const props = defineProps<{
  item: QaCollectionState
  collection: QaCollectionState[]
  index: number
}>()

const $emits = defineEmits<{
  (e: 'sub', value: string): void
  (e: 'gen', value: QaCollectionState): void
}>()

const { item, collection, index } = toRefs(props)
const qaStore = useQaStore()
const { qaState } = storeToRefs(qaStore)

function completeNext(item: QaCollectionState) {
  item.progress = QaProgressState.Analyze
  qaStore.ask(item.id)
}

function handleSub(id: string) {
  $emits('sub', id)
}

function handleGen(item: QaCollectionState) {
  $emits('gen', item)
}

const isLast = computed(() => {
  return index.value === (collection.value.length - 1)
})

const currentPair = computed(() => {
  return item.value.pairs.find(i => i._id === item.value.curPairId)
})

const isVisibleTimeline = computed(() => {
  if (item.value.progress === QaProgressState.Supplement)
    return false

  if (item.value.progress !== QaProgressState.Finish) {
    if (item.value.currentSearchMode === 'pro')
      return true
    else
      return false
  }

  if (item.value.currentSearchMode === 'pro')
    return true
  else
    return false
})
</script>

<template>
  <div
    :id="item.id"
    class="flex relatvie pt-[56px] justify-center"
  >
    <template v-if="item.progress === QaProgressState.Supplement && item.curAdditional">
      <QaComplete
        :progress="item.progress"
        :data="item.curAdditional"
        @next="completeNext(item)"
      />
    </template>
    <template v-else>
      <div class="w-full flex" :class="{ 'h-full': collection.length === 1, 'justify-center': item.currentSearchMode === 'lite' }">
        <div
          class="flex flex-col w-[660px] relative"
          :class="{
            'pb-[56px]': index !== collection.length - 1,
          }"
        >
          <div
            class="mb-[20px] text-[30px] leading-[42px] font-600 text-[rgba(0,0,0,0.9)]"
          >
            {{ item.query }}
          </div>
          <QaProgress :progress="item.progress" />
          <QaCollCom :is-last="isLast" :data="item" @sub="handleSub" @gen="handleGen(item)" />
          <slot></slot>
        </div>
        <template
          v-if="isVisibleTimeline"
        >
          <QaTimeline :data="item" :time-line-index="index" :collection="collection" :progress="item.progress" />
        </template>
      </div>
    </template>
  </div>
  <div
    v-if="index !== collection.length - 1" class="h-[1px] bg-[#EEEEEE]"
    :class="{
      'w-full': qaState.mode !== QaMode.DOC,
      'w-[660px]': qaState.mode === QaMode.DOC,
    }"
  />
</template>
