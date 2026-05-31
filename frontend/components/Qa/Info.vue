<script setup lang="ts">
const props = defineProps<{
  modelValue: boolean
  qaInfo: QaPairInfo
  searchMode: string
}>()

const $emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'morePages'): void
}>()

const { modelValue, qaInfo } = toRefs(props)

const sites = computed(() => {
  return qaInfo.value.ref_pages_list.slice(0, 3)
})
const sitesIcon = computed(() => {
  const icons = qaInfo.value.ref_pages_list.filter(site => site.icon).map(site => site.icon)
  if (icons.length === 0)
    return []
  return [...new Set(icons)].slice(0, 3)
})

function handleModel(value: boolean) {
  $emit('update:modelValue', value)
}

const headerText = computed(() => {
  if (props.searchMode === 'doc')
    return `总结${qaInfo.value.page_num}篇文档，参考约${number2txt(qaInfo.value.word_num || 0, 10000) || 0}字生成以下答案`
  return `总结${qaInfo.value.site_num || 0}个网站，参考${qaInfo.value.page_num || 0}篇报道(${number2txt(qaInfo.value.word_num || 0, 10000) || 0}字) 生成以下答案`
})
</script>

<template>
  <MCollapse
    :model-value="modelValue"
    class="w-[660px]"
    :disabled="props.searchMode === 'doc'"
    @update:model-value="handleModel"
  >
    <template #header>
      <div class="w-full flex items-center">
        <div class="i-ll-magic text-normal-color text-[16px]" />
        <span class="text-[14px] leading-normal ml-[4px] text-[#333]">{{ props.searchMode === 'doc' ? '文件搜索' : '全网搜索' }}</span>
        <div class="mx-[8px] w-[1px] h-[12px] bg-[#4044ED] opacity-[0.4]" />
        <span class="text-[14px] font-normal leading-normal text-[rgba(0,0,0,0.6)]">
          {{ headerText }}
        </span>
      </div>
    </template>
    <template #default>
      <div v-if="modelValue" class="flex flex-col gap-y-[20px]">
        <div v-if="qaInfo.additional_query?.selected_option && qaInfo.additional_query.selected_option.length > 0" class="flex flex-col gap-y-[8px]">
          <div class="flex items-center">
            <div class="i-ll-report text-[16px] text-[rgba(0,0,0,0.6)]" />
            <span class="ml-[4px] text-[14px] font-500 leading-[20px] text-[#333]">补充信息</span>
          </div>
          <div class="pt-[8px] text-[12px] leading-[17px] text-[rgba(0,0,0,0.6)]">
            {{ qaInfo.additional_query?.title }}
          </div>
          <div v-if="qaInfo.additional_query?.options" class="flex items-center flex-wrap gap-[8px]">
            <div
              v-for="item in qaInfo.additional_query.selected_option.slice(0, 5)"
              :key="item"
              class="rounded-[20px] flex items-center justify-center px-[8px] py-[3.5px] text-[12px] text-[#666] border bg-[#FFF] border border-[#D9D9D9] leading-[17px] truncate"
            >
              {{ item }}
            </div>
          </div>
        </div>
        <div v-if="qaInfo.search_query.length > 0" class="flex flex-col gap-y-[8px]">
          <div class="flex items-center">
            <div class="i-ll-file-search text-[16px] text-[rgba(0,0,0,0.6)]" />
            <span class="ml-[4px] text-[14px] leading-[20px] text-[#333]">检索关键词</span>
          </div>
          <div class="flex items-center gap-[8px] flex-wrap">
            <div
              v-for="item in qaInfo.search_query.slice(0, 10)"
              :key="item"
              class="rounded-[20px] flex items-center justify-center px-[8px] py-[2.5px] border bg-[#FFF] border border-[#D9D9D9] truncate"
            >
              <el-tooltip
                effect="dark"
                placement="bottom"
              >
                <template #content>
                  <div class="w-[213px]">
                    <span>{{ item }}</span>
                  </div>
                </template>
                <span class="text-[12px] text-[#666] leading-[17px]">{{ item.length > 15 ? `${item.slice(0, 15)}...` : item }}</span>
              </el-tooltip>
            </div>
          </div>
        </div>
        <div v-if="sites.length > 0" class="flex flex-col gap-y-[8px]">
          <div class="flex items-center">
            <div class="i-ll-compass text-[16px] text-[rgba(0,0,0,0.6)]" />
            <div class="ml-[4px] text-[14px] leading-[20px] text-[#333]">
              来源
            </div>
            <div class="ml-[4px] text-[12px] leading-[17px] text-[rgba(0,0,0,0.6)]">
              {{ `(共${qaInfo.page_num}篇，约${number2txt(qaInfo.word_num, 10000)}字)` }}
            </div>
          </div>
          <div class="flex items-center">
            <NuxtLink
              v-for="(site) in sites"
              :key="site._id"
              class="!no-underline"
              :href="site.url"
              target="_blank"
            >
              <div
                class="w-[160px] h-[71px] rounded-[7px] p-[8px] border border-[0.5px] border-[#D9D9D9] relative mr-[8px] hover:border-[#4044ED] cursor-pointer flex flex-col justify-between"
              >
                <div class="text-hidden-2 h-[34px] text-[12px] leading-[17px] text-[rgba(0,0,0,0.9)]">
                  {{ site.title }}
                </div>
                <div class="flex items-center">
                  <img
                    v-if="site.icon"
                    class="h-[12px] w-[12px] rounded-full overflow-hidden mr-[4px]"
                    :src="site.icon"
                  >
                  <div v-else class="i-ll-earth text-[12px]  text-[#d8d8d8] mr-[4px]" />

                  <div class="w-[108px] truncate text-[12px] leading-[17px] text-[rgba(0,0,0,0.6)]">
                    {{ site.site }}
                  </div>
                </div>
                <div v-if="site.index" class="absolute bottom-[10.5px] right-[8px] rounded-full flex items-center justify-center bg-[#F3F3F3] w-[12px] h-[12px]">
                  <span class="text-[10px] font-bold leading-[10px] text-[rgba(0,0,0,0.4)]">{{ site.index }}</span>
                </div>
              </div>
            </NuxtLink>
            <div
              class="w-[132px] h-[71px] rounded-[7px] p-[8px] border border-[0.5px] border-[#D9D9D9] relative hover:border-[#4044ED] cursor-pointer flex flex-col justify-between"
              @click="$emit('morePages')"
            >
              <div class="text-[12px] text-[rgba(0,0,0,0.6)]">
                {{ `查看全部（${qaInfo.page_num}）` }}
              </div>
              <div class="relative h-[12px]">
                <img
                  v-for="(icon, index) in sitesIcon"
                  :key="icon"
                  class="absolute w-[12px] h-[12px] rounded-full overflow-hidden top-0"
                  :src="icon"
                  :style="{
                    left: `${index * 10}px`,
                  }"
                >
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </MCollapse>
</template>
