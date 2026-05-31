<script setup lang="ts">
import type { QaCollectionState } from '~/store/qa'
import { QaMode, useQaStore } from '~/store/qa'

const props = defineProps<{
  modelValue: boolean
  qaInfo: QaPairInfo
  collection: QaCollectionState
}>()

const $emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'generate'): void
}>()
const { modelValue, qaInfo, collection } = toRefs(props)
const count = 100
const currPairPageSum = computed(() => {
  const num_ = Math.floor(qaInfo.value.page_num / count)
  const num = qaInfo.value.page_num / count
  if (num > num_)
    return num_ + 1

  return num_
})

const qaStore = useQaStore()
const { qaState } = storeToRefs(qaStore)

const pages = computed(() => {
  // if (qaState.value.mode === QaMode.WEB)
  //   return qaInfo.value.ref_pages_list
  // else
  //   return qaInfo.value.ref_docs_list
  return qaInfo.value.ref_pages_list
})

const currentPageIndex = ref(0)
const pagesArr = computed(() => {
  const res = []
  for (let i = 0; i < currPairPageSum.value; i++)
    res.push(pages.value.slice(i * count, (i + 1) * count))
  return res
})

function beforePage() {
  if (currentPageIndex.value > 0)
    currentPageIndex.value--
}

function afterPage() {
  if (currentPageIndex.value < (pagesArr.value.length - 1))
    currentPageIndex.value++
}

function handleCheckBoxChange(check: boolean, page: RefPage) {
  if (check)
    collection.value.curDeleteNews.push(page._id)
  else
    collection.value.curDeleteNews = collection.value.curDeleteNews.filter(item => item !== page._id)
}

function cancel() {
  $emit('update:modelValue', false)
}

function beforeClose() {
  collection.value.curDeleteNews = []
  currentPageIndex.value = 0
}

function generate() {
  if (collection.value.curDeleteNews.length === 0) {
    ElMessage({
      message: '请至少勾选1个来源',
      type: 'warning',
      customClass: '!z-[10000]',
    })
    return
  }
  $emit('update:modelValue', false)
  $emit('generate')
}

function handleModelValue(event: boolean) {
  $emit('update:modelValue', event)
}

const headerText = computed(() => {
  if (qaState.value.mode === QaMode.WEB)
    return `（共${qaInfo.value.page_num}篇，约${number2txt(qaInfo.value.word_num, 10000)}字）`
  else
    return `（共${qaInfo.value.doc_num}篇，约${number2txt(qaInfo.value.word_num, 10000)}字）`
})
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    direction="rtl"
    class="!w-[500px]"
    @before-close="beforeClose"
    @update:model-value="handleModelValue"
  >
    <template #header>
      <div class="flex items-center">
        <span class="text-[16px] font-600 leading-[24px] text-[rgba(0,0,0,0.9)]">来源</span>
        <span class="text-[12px] font-500 text-[rgba(0,0,0,0.6)]">
          {{ headerText }}
        </span>
      </div>
    </template>
    <template #default>
      <!-- <div class="text-[12px] pt-[16px] px-[16px] text-[rgba(0,0,0,0.6)] mb-[12px]">
        可批量勾选删除来源，并重新生成答案
      </div> -->
      <div class="h-[16px] w-full" />
      <div class="h-[calc(100vh-117px)] w-full overflow-y-scroll">
        <div
          v-for="(page, index) in pagesArr[currentPageIndex]"
          :key="page._id"
          class="w-full px-[16px] flex items-start"
        >
          <!-- <el-checkbox
            :checked="collection.curDeleteNews.includes(page._id)"
            class="!h-[16px] pt-[16px]"
            @change="handleCheckBoxChange($event as boolean, page)"
          /> -->
          <NuxtLink :href="page.url" target="__blank" class="!hover:no-underline">
            <div class="w-[444px] ml-[8px] mb-[16px] p-[8px] bg-[#F5F6F7] rounded-[6px] relative">
              <div class="w-full truncate mb-[8px] text-[12px] font-500 text-[rgba(0,0,0,0.9)]">
                {{ page.title }}
              </div>
              <div class="text-hidden-3 mb-[8px] text-[12px] text-[rgba(0,0,0,0.6)]">
                {{ page.summary }}
              </div>
              <div class="flex items-center justify-between">
                <div class="flex items-center">
                  <img
                    v-if="page.icon"
                    class="h-[12px] w-[12px] rounded-full overflow-hidden mr-[4px]"
                    :src="page.icon"
                  >
                  <div v-else class="i-ll-earth text-[12px]  text-[#d8d8d8] mr-[4px]" />
                  <div class="w-[395px] truncate text-[12px] text-[rgba(0,0,0,0.6)]">
                    {{ page.site }}
                  </div>
                </div>
                <div v-if="page.index" class="w-[12px] h-[12px] flex items-center justify-center rounded-full bg-[#F3F3F3]">
                  <div class="text-[10px] text-[rbga(0,0,0,0.4)]">
                    {{ index + 1 }}
                  </div>
                </div>
              </div>
            </div>
          </NuxtLink>
        </div>
      </div>
      <div class="w-full h-[56px] flex items-center justify-between px-[16px]">
        <div class="flex items-center">
          <div
            class="i-ll-arrow-left text-[18px] origin-center cursor-pointer mr-[2px]" :class="{
              'cursor-not-allowed': currentPageIndex === 0,
              'text-[rgba(0,0,0,0.4)]': currentPageIndex === 0,
            }"
            @click="beforePage()"
          />
          <div class="text-[14px] text-[#262626]">
            <span>{{ currentPageIndex + 1 }}</span>
            <span> / {{ currPairPageSum }}</span>
          </div>
          <div
            class="i-ll-arrow-left rotate-180 text-[18px] cursor-pointer ml-[2px]"
            :class="{
              'cursor-not-allowed': (currentPageIndex + 1) === currPairPageSum,
              'text-[rgba(0,0,0,0.4)]': (currentPageIndex + 1) === currPairPageSum,
            }"
            @click="afterPage()"
          />
        </div>
        <div class="footer">
          <!-- <span class="text-[12px] text-[rgba(0,0,0,0.6)]">{{ `已勾选${collection.curDeleteNews.length}篇来源` }}</span>
          <el-button class="!bg-[#E7E7E7] ml-[12px] mr-[8px]" round @click="cancel">
            <span class="text-[14px] leading-[22px] font-normal ">取消</span>
          </el-button>
          <el-button
            :class="{
              '!bg-[#E7E7E7]': collection.curDeleteNews.length === 0,
              '!bg-[#4044ED]': collection.curDeleteNews.length > 0,
            }"
            round @click="generate"
          >
            <span
              class="text-[14px] leading-[22px] font-normal" :class="{
                'text-[#fff]': collection.curDeleteNews.length > 0,
              }"
            >删除，并重新生成答案</span>
          </el-button> -->
        </div>
      </div>
    </template>
  </el-drawer>
</template>

<style lang="scss" scoped>
.footer:deep(.el-button:hover) {
  border-color: transparent !important;
    color: inherit !important;
}
</style>
