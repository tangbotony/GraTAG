<script setup lang="ts">
import type { UploadUserFile } from 'element-plus'
import { QaMode } from '~/store/qa'
import type { rowType } from '~/components/Upload2.vue'

definePageMeta({
  middleware: 'auth',
  keepalive: true,
  layout: 'base',
  key: 'search',
})

const searchMode = ref(QaMode.WEB)
const isPro = ref(currentUser.value?.extend_data?.is_qa_pro || false)
const fileList = ref<UploadUserFile[]>([])
watch(isPro, (val) => {
  if (val !== !!currentUser.value?.extend_data?.is_qa_pro)
    updateUserInfo('is_qa_pro', val)
})

watch(() => !!currentUser.value?.extend_data?.is_qa_pro, (val) => {
  if (val !== isPro.value)
    isPro.value = val
})

const {
  search,
  fullScreen,
  filterrecomData,
  searchState,
  handleDeleteRecomItem,
  handleClearAllRecom,
  handleSearch,
  handleOutside,
  handleFocus,
  bestRecomdata,
  handleRecomSelect,
  handleAsk,
} = useQaSearch(searchMode, fileList)

const historyOpen = ref(false)

const historyCount = ref(0)
function handleHistoryChange(count: number) {
  historyCount.value = count
}

const baseURL = import.meta.env.VITE_API
const uploadUrl = ref(`${baseURL}api/doc_search/upload`)
// const uploadUrl = ref(`${baseURL}/api/material/upload`)
function handleUploadSuccess() {

}

function handleUploadCancel(row: rowType) {
  fileList.value = fileList.value.filter(i => i.uid !== row.data.uid)
}

function handleUploadDelete(row: rowType) {
  fileList.value = fileList.value.filter(i => i.uid !== row.data.uid)
}
</script>

<template>
  <div class="flex h-full">
    <div v-if="historyOpen" class="shrink-0 w-[248px] p-[24px] relative">
      <div class="text-[18px] font-600 leading-normal mb-[24px]">
        历史记录
      </div>
      <div class="w-[24px] h-[24px] rounded-[4px] hover:bg-[#F3F3F3] flex items-center justify-center top-[26px] right-[16px] absolute">
        <div
          class="i-ll-fold-2 text-[16px] cursor-pointer text-[#666] hover:text-[rgba(0,0,0,0.9)]"
          @click="historyOpen = !historyOpen"
        />
      </div>
      <div class="w-full h-[calc(100vh-75px)] overflow-y-scroll search-history-c">
        <SearchHistory
          @change="handleHistoryChange"
        />
      </div>
    </div>
    <div id="search-container" class="search-container flex-1 h-full flex relative rounded-l-[24px]">
      <div
        class="search-scrollar w-full h-[calc(100vh-48px)] mt-[24px] flex flex-col items-center"
        :class="{
          'overflow-y-scroll': !fullScreen,
          'overflow-y-hidden': fullScreen,
        }"
      >
        <div class="w-full h-[176px] shrink-0" />
        <div class="text-[24px] font-normal leading-normal text-center text-black mb-[7px]">
          有什么可以为您服务的吗？
        </div>
        <div class="w-full flex justify-center mb-[32px] mt-[24px]">
          <SearchBtnSwitch v-model="searchMode" />
        </div>
        <!-- <div class="text-[14px] font-normal leading-normal text-center text-[rgba(0,0,0,0.45)] mb-[32px]" /> -->
        <template v-if="searchMode === QaMode.WEB">
          <SearchInput
            v-model="search"
            v-model:fullScreen="fullScreen"
            v-model:isPro="isPro"
            :search-mode="searchMode"
            :options="filterrecomData"
            :state="searchState"
            @delete="handleDeleteRecomItem"
            @clear-all="handleClearAllRecom"
            @ask="handleAsk"
            @search="handleSearch"
            @focus="handleFocus"
            @outside="handleOutside"
          />

          <SearchRecom
            :data="bestRecomdata"
            @select="handleRecomSelect"
          />
        </template>
        <template v-else>
          <SearchInput
            v-model="search"
            v-model:fullScreen="fullScreen"
            v-model:isPro="isPro"
            :search-mode="searchMode"
            :options="filterrecomData"
            :state="searchState"
            @delete="handleDeleteRecomItem"
            @clear-all="handleClearAllRecom"
            @ask="handleAsk"
            @search="handleSearch"
            @focus="handleFocus"
            @outside="handleOutside"
          />
          <div class="w-[700px] mt-[24px] mb-[4px]">
            <Upload2
              v-model:file-list="fileList"
              size="medium"
              :drag="true"
              :action="uploadUrl"
              @success="handleUploadSuccess"
              @cancel="handleUploadCancel"
              @delete="handleUploadDelete"
            />
          </div>
        </template>
      </div>
      <div
        v-if="!historyOpen"
        class="absolute left-[24px] top-[60px] bg-white rounded-full w-[36px] h-[36px] flex items-center justify-center cursor-pointer hover:bg-[#F3F3F3]"
        :class="{
          hidden: historyCount === 0,
        }"
        @click="historyOpen = !historyOpen"
      >
        <div class="i-ll-history text-[20px] text-[rgba(0,0,0,0.6)] hover:text-[rgba(0,0,0,0.9)]" />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.search-container {
  background-size: 100%, auto, cover;
  background-repeat: no-repeat;
  background-image: url('~/assets/images/search/bg.jpeg');
}

.search-scrollar {
  &::-webkit-scrollbar {
    display: none;
  }
  -ms-overflow-style: none;  /* IE and Edge */
  scrollbar-width: none;  /* Firefox */
}

.search-history-c {
  -ms-overflow-style: none;  /* IE and Edge */
  scrollbar-width: none;  /* Firefox */
}
.search-history-c::-webkit-scrollbar {
  display: none;
}
</style>
