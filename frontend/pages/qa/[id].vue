<script setup lang="ts">
import type { QaCollectionState } from '~/store/qa'
import { QaAnswerType, QaMode, QaProgressState, useQaStore } from '~/store/qa'

definePageMeta({
  middleware: 'auth',
  layout: 'base',
  key: 'qa-id',
  name: 'qa-id',
})

const route = useRoute()
const qaStore = useQaStore()
const { subscribe, createCollection, completeOrReject, getSeries, createPair, getFileList } = qaStore
const { qaState, scrollerContainer } = storeToRefs(qaStore)

const collection = computed(() => {
  return qaState.value.collection
})

if (route.params.id)
  qaState.value.seriesId = route.params.id as string

onUnmounted(() => {
  qaStore.reset()
})

onBeforeMount(async () => {
  const collection = qaState.value.collection.find(i => i.progress === QaProgressState.Analyze)
  if (collection)
    completeOrReject(collection)
  if (collection && qaState.value.mode === QaMode.DOC) {
    // createPair(collection)
    getFileList(qaState.value.seriesId)
  }

  if (qaState.value.collection.length === 0) {
    await getSeries()
    await nextTick()
    setTimeout(() => {
      const item = qaState.value.collection.find(i => i.is_subscribed)
      if (item) {
        const id = item.id
        document.getElementById(`${id}`)?.scrollIntoView({ behavior: 'smooth' })
      }
    }, 300)
  }
})

const addQuery = ref('')
const containerScrollRef = ref()
async function appendAsk(e: KeyboardEvent | Event) {
  if ((e as KeyboardEvent).isComposing)
    return

  if ((e as KeyboardEvent).shiftKey)
    return

  e.preventDefault()

  if (addQuery.value.trim().length === 0)
    return
  createCollection(QaAnswerType.Append, addQuery.value)
  addQuery.value = ''
}

const router = useRouter()
function goSearch() {
  router.push('/search')
}

const visibleHistory = ref(false)
function showHistory() {
  visibleHistory.value = true
}

const subModelVisible = ref(false)
const currentSubCollectionId = ref('')
async function handleSub(collection_id: string) {
  const collection = qaState.value.collection.find(i => i.id === collection_id)
  if (!collection)
    return

  if (collection.is_subscribed) {
    const { error } = await useDeleteQaSubscribe({ qa_pair_collection_id: collection_id })
    if (!error.value)
      collection.is_subscribed = false

    return
  }
  currentSubCollectionId.value = collection_id
  subModelVisible.value = true
}
function handleSubscribe(data: {
  push_interval: string
  push_time: string
  end_time: string
  email: string }) {
  subscribe({
    ...data,
    qa_pair_collection_id: currentSubCollectionId.value,
  })
}

const genNewModelVisible = ref(false)
const genNewData = ref('')
function handleGen(item: QaCollectionState) {
  const pair = item.pairs.find(i => i._id === item.curPairId)
  if (!pair || !pair.general_answer)
    return
  genNewData.value = md2Text(pair.general_answer)
  genNewModelVisible.value = true
}

onMounted(() => {
  scrollerContainer.value = containerScrollRef.value
})

const isLoading = computed(() => {
  return qaState.value.collection.some(i => i.progress !== QaProgressState.Finish)
})

const isLoadingWithoutSupplement = computed(() => {
  return qaState.value.collection.some(i => i.progress !== QaProgressState.Finish && i.progress !== QaProgressState.Supplement)
})

function handleStopCollection() {
  qaStore.stopCollection()
}

const isPro = ref(!!currentUser.value?.extend_data?.is_qa_pro)
watch(isPro, (val) => {
  if (val !== !!currentUser.value?.extend_data?.is_qa_pro)
    updateUserInfo('is_qa_pro', val)
})
watch(() => !!currentUser.value?.extend_data?.is_qa_pro, (val) => {
  if (val !== isPro.value)
    isPro.value = val
})

const isCenterApendAskBox = computed(() => {
  if (collection.value.length === 0)
    return false
  const lastItem = collection.value[collection.value.length - 1]
  return lastItem.currentSearchMode === 'lite'
})
</script>

<template>
  <div class="qa-container relative px-[93px] flex flex-col items-center">
    <div
      ref="containerScrollRef"
      class="h-screen w-[1054px] overflow-scroll qa-item-container relative"
    >
      <QaItem
        v-for="(item, index) in collection"
        :key="item.id"
        :item="item"
        :collection="collection"
        :index="index"
        @sub="handleSub"
        @gen="handleGen"
      >
        <div v-if="(collection.length > 0) && (index === (collection.length - 1)) && !isLoading" class="w-full flex pb-[32px] items-center">
          <div class="flex items-center w-[660px] h-full ">
            <div
              class="w-full input-container relative" :class="{
                'is-web': qaState.mode === QaMode.WEB,
              }"
            >
              <!-- eslint-disable-next-line vue/no-deprecated-v-on-native-modifier -->
              <el-input
                v-model="addQuery"
                type="textarea"
                :rows="1"
                class="h-[48px] !w-[660px] flex items-center "
                placeholder="继续追问"
                @keydown.enter="appendAsk($event)"
              />

              <div v-if="qaState.mode === QaMode.WEB" class="absolute top-[13px] right-[48px]">
                <SearchSwitch v-model="isPro" />
              </div>

              <div
                class="i-ll-send text-[28px] absolute top-[10px] right-[12px]"
                :class="{
                  'text-[#d8d8d8]': addQuery.length === 0,
                  'text-[#4044ED]': addQuery.length > 0,
                  'cursor-pointer': addQuery.length > 0,
                }"
                @click="appendAsk($event)"
              />
            </div>
          </div>
        </div>
      </QaItem>
    </div>
    <div v-if="qaState.docs.length > 0 && qaState.mode === QaMode.DOC" class="w-[1054px] absolute top-0 left-50% translate-x-[-50%]">
      <QaDocList />
    </div>
    <div
      v-if="isLoadingWithoutSupplement"
      class="w-[1054px] absolute bottom-[48px] left-50% translate-x-[-50%] flex"
      :class="{ 'justify-center': isCenterApendAskBox }"
    >
      <div class="flex items-center justify-center w-[660px] ">
        <QaStop
          @stop="handleStopCollection()"
        />
      </div>
    </div>
    <div class="btn-circle cursor-pointer absolute top-[59px] left-[35px]" @click="goSearch">
      <div class="i-ll-plus text-[20px] text-[#4044ED]" />
    </div>
    <div
      class="btn-circle cursor-pointer absolute top-[107px] left-[35px]"
      @click="showHistory"
    >
      <div class="i-ll-history text-[20px] text-[rgba(0,0,0,0.6)]" />
    </div>
    <QaHistory v-model="visibleHistory" />
    <QaSub v-model="subModelVisible" @sub="handleSubscribe" />
    <QaGenNew v-model="genNewModelVisible" :answer="genNewData" />
    <QaTooltip />
  </div>
</template>

<style lang="scss" scoped>
.qa-container {
  background-size: 100%, 240px, cover;
  background-repeat: no-repeat;
  background: linear-gradient(180deg, #F0F3FF 0%, #FFFFFF 100%);
  min-width: 1240px;
}

.qa-item-container {
  &::-webkit-scrollbar {
    display: none;
  }
  -ms-overflow-style: none;  /* IE and Edge */
  scrollbar-width: none;  /* Firefox */
}

.input-container.is-web:deep(.el-textarea) {
  padding-right: 104px !important;
}

.input-container:deep(.el-textarea) {
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  border-radius: 12px !important;
  padding-right: 48px;
  display: flex;
  align-items: center;
}

.input-container:deep(.el-textarea__inner) {
  border: none;
  box-shadow: none;
  margin-left: 1px;
  resize: none;
  background: transparent !important;
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
