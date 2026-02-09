<script setup lang="ts">
import { QaProgressState, useQaStore, QaAnswerType } from '~/store/qa'

definePageMeta({
  middleware: 'auth',
  layout: 'base',
  key: 'qa',
  name: 'qa',
})

const store = useQaStore()
const { createSeries, beforeAsk } = store
const { qaState } = storeToRefs(store)
const router = useRouter()
onBeforeMount(async () => {
  const query = qaState.value.firstQuery
  const res = await createSeries(query)
  if (res) {
    beforeAsk(res.qa_pair_collection_id, res.qa_series_id, query, QaAnswerType.First)
    router.replace(`/qa/${res.qa_series_id}`)
  }
})

const isPro = computed(() => {
  return !!currentUser.value?.extend_data?.is_qa_pro
})
</script>

<template>
  <div class="qa-container relative">
    <div
      class="h-screen w-full"
    >
      <div
        class="flex justify-center relatvie pt-[56px] min-h-screen px-[93px]"
      >
        <div
          class="w-[1054px] flex flex-col min-h-[calc(100vh-56px)]"
          :class="{
            'w-[1054px]': isPro,
            'w-[660px]': !isPro,
          }"
        >
          <div
            class="mb-[20px] shrink-0 text-[30px] font-600 text-[rgba(0,0,0,0.9)] w-[660px]"
          >
            {{ qaState.firstQuery }}
          </div>
          <div class="flex flex-[1_1_0px]">
            <div
              class="flex flex-col w-[660px] relative h-full pb-[80px]"
            >
              <QaProgress :progress="QaProgressState.Analyze" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.qa-container {
  background-size: 100%, 240px, cover;
  background-repeat: no-repeat;
  background: linear-gradient(180deg, #F0F3FF 0%, #FFFFFF 100%);
}

.input-container:deep(.el-input__wrapper) {
  border-radius: 12px !important;
  padding-right: 48px;
}

.btn-circle {
  width: 36px;
  height: 36px;
  border-radius: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #FFFFFF;
  border: 1px solid #E5E6FF;
  box-shadow: 0px 4px 10px 0px rgba(0, 0, 0, 0.04);
}

.list {
  .item {
    border-bottom: 1px solid #EEEEEE;
  }
  .item:last-child {
    border-bottom: none;
  }
}
</style>
