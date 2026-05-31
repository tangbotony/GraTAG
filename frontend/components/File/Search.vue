<script setup lang="ts">
import type { FileType } from '~/composables/api/file'
import type { FolderType } from '~/composables/api/folder'

const inputSearch = ref('')
const searchResult = ref<(FolderType | FileType)[]>([])

const isSearched = ref(false)
const isDataInit = ref(false)
const isloading = ref(false)

async function handleSearch() {
  if (inputSearch.value.length === 0)
    return

  isSearched.value = true
  isloading.value = true
  const { data, error } = await useFileSearch({
    search_text: inputSearch.value,
    parent_id: fileState.value.currentFolder,
  })
  if (data.value?.meta)
    searchResult.value = data.value.meta

  isDataInit.value = true
  isloading.value = false
}

const debounceSearch = useDebounceFn(handleSearch, 300)

const searchRef = ref<HTMLElement>()

onClickOutside(searchRef, () => {
  isSearched.value = false
})

watch(isSearched, (val) => {
  if (!val) {
    inputSearch.value = ''
    searchResult.value = []
    isDataInit.value = false
  }
})

function handleFile(item: FileType | FolderType) {
  if (item.type === 'document')
    navigateTo(`/document/${item._id}`)

  else if (item.type === 'folder')
    moveFilePath(item.path, item.path.slice(-2)[0])

  isSearched.value = false
}
</script>

<template>
  <div ref="searchRef" class="input-container relative z-10">
    <el-input
      v-model="inputSearch"
      placeholder="搜索"
      @input="debounceSearch"
    >
      <template #append>
        <el-button @click="isSearched = !isSearched">
          <div
            :class="{
              'i-ll-search': !isSearched,
              'i-ll-close': isSearched,
            }"
          />
        </el-button>
      </template>
    </el-input>
    <div
      v-show="isSearched"
      v-loading="isloading"
      class="list-container"
    >
      <div class="list">
        <template v-if="!isDataInit || searchResult.length > 0">
          <div
            v-for="item in searchResult"
            :key="item._id"
            class="item"
          >
            <div class="flex items-center cursor-pointer" @click="handleFile(item)">
              <div
                class="text-normal-color mr-[4px] ml-[8px]"
                :class="{
                  'i-ll-folder': item.type === 'folder',
                  'i-ll-file': item.type === 'document',
                }"
              />
              <div>
                <div class="truncate max-w-[315px]">
                  <FileSearchText
                    :text="item.name"
                    :search-text="inputSearch"
                  />
                </div>
                <div class="text-search-info flex items-center">
                  <span>所在位置：{{ item.path[item.path.length - 2][1] }}</span>
                  &nbsp;&nbsp;<div class="divider" /> &nbsp;&nbsp;
                  <span>所有者： 我</span>
                  &nbsp;&nbsp;<div class="divider" />&nbsp;&nbsp;
                  <span>更新时间：{{ formatterDate(item) }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>
        <template v-else>
          <div class="flex items-center justify-center h-[154px] w-full">
            <div class="flex flex-col items-center">
              <img class="w-[121px] h-[99px]" src="~/assets/images/empty.png">
              <div class="text-empty">
                无搜索结果
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.input-container {
    &:deep( .el-input-group__append ) {
        background-color: transparent
    }

    &:deep(.el-input__wrapper) {
        width: 313px;
        height: 32px;
    }

    &:deep(button) {
        width: 37px;
        display: flex;
        justify-content: center;
        align-items: center;
    }
}

.list-container {
  position: absolute;
  top: 58px;
  left: -12px;
  width: 425px;
  padding: 24px;
  align-items: flex-start;
  flex-shrink: 0;
  align-self: stretch;
  border-radius: 20px;
  background:  #FFF;

  /* drop-shadow/0.12+0.8+0.5 */
  box-shadow: 0px 9px 28px 8px rgba(0, 0, 0, 0.05), 0px 6px 16px 0px rgba(0, 0, 0, 0.08), 0px 3px 6px -4px rgba(0, 0, 0, 0.12);
  box-sizing: border-box;
  max-height: 300px;
  overflow: hidden;

  .list {
    width: 377px;
    max-height: 252px;
    overflow-y: scroll;
    overflow-x: hidden;
    .item {
      width: 100%;
      height: 72px;
      display: flex;
      align-items: center;

      &:not(last-child) {
        margin-bottom: 10px;
      }

      &:hover {
        background-color: #f5f5f5;
      }
    }
  }
}

.text-search-info {
  color: var(--c-text-gray, rgba(0, 0, 0, 0.45));
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  line-height: 20px;
}

.divider {
  width: 1px;
  height: 14px;
  background: rgba(0,0,0,0.45);
}

.text-empty {
  color: var(--c-text-black, rgba(0, 0, 0, 0.85));
  text-align: center;
  font-size: 14px;
  font-style: normal;
  font-weight: 400;
  line-height: 22px; /* 157.143% */
}
</style>
