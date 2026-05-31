<script setup lang="ts">
import type { QaCollectionState } from '~/store/qa'
import { QaAnswerType, QaProgressState, useQaStore } from '~/store/qa'

const props = defineProps<{
  data: QaCollectionState
  isLast: boolean
}>()

const $emit = defineEmits<{
  (e: 'sub', id: string): void
  (e: 'gen'): void
}>()

const { data, isLast } = toRefs(props)
const qaStore = useQaStore()

const isOpenCollapse = ref(false)

const currentPair = computed(() => {
  const p = data.value.pairs.find(item => item._id === data.value.curPairId)
  return p
})
const isOpenDrawer = ref(false)

const isVisibleContent = computed(() => {
  if (data.value.progress === QaProgressState.Complete)
    return true
  if (data.value.progress === QaProgressState.Finish)
    return true
  if (data.value.progress === QaProgressState.TextEnd)
    return true
  return false
})

async function appendAsk(query: string) {
  if (query.trim().length === 0)
    return
  qaStore.createCollection(QaAnswerType.Recommend, query)
}

function sub() {
  $emit('sub', data.value.id)
}

function gen() {
  $emit('gen')
}

function reGenerateWidthDelete(id: string) {
  qaStore.reAsk(id, QaAnswerType.DeleteRef)
}
</script>

<template>
  <div class="w-[660px] flex flex-col">
    <template v-if="currentPair">
      <QaInfo
        v-if="currentPair?.qa_info && isVisibleContent"
        v-model="isOpenCollapse"
        :qa-info="currentPair.qa_info"
        :searchMode="currentPair.search_mode"
        @more-pages="isOpenDrawer = true"
      />
      <QaPages
        v-if="currentPair?.qa_info"
        v-model="isOpenDrawer"
        :qa-info="currentPair.qa_info"
        :collection="data"
        @generate="reGenerateWidthDelete(data.id)"
      />
      <QaContent
        v-if="isVisibleContent"
        :id="data.id"
        :content="currentPair.general_answer || ''"
        :progress="data.progress"
        :collection="data"
        @sub="sub"
        @gen="gen"
      />
      <template v-if="isLast && isVisibleContent && currentPair.recommend_query && currentPair.recommend_query.length > 0">
        <div class="text-[16px] text-[#24292F] mb-[12px] mt-[32px]">
          参考问题
        </div>
        <div class="flex flex-wrap gap-[8px] pb-[32px]">
          <div
            v-for="item in currentPair.recommend_query"
            :key="item"
            class="recom-item"
            @click="appendAsk(item)"
          >
            {{ item }}
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.recom-item {
  padding: 6px 16px;
  border-radius: 20px;
  background: #FFFFFF;
  border: 1px solid rgba(0, 0, 0, 0.15);
  font-size: 14px;
  font-weight: normal;
  line-height: normal;
  color: rgba(0, 0, 0, 0.6);
  cursor: pointer;
  &:hover {
    color: #4044ED;
    border-color: #4044ED;
  }
}
</style>
