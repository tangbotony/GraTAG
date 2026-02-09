<script lang="ts" setup>
const props = defineProps<{
  placeholder?: string
  modelValue: string
  currentUrl: string
}>()

const $emit = defineEmits<{
  (e: 'update:model-value', value: string): void
  (e: 'select', value: { title: string; abstract: string; url: string }): void
  (e: 'update:currentUrl', value: string): void
}>()

const list = ref<{ title: string; abstract: string; url: string; isHover: boolean }[]>([])
const visible = ref(false)
const popover = ref()
const input = ref()

const generateEventId = inject<Ref<string>>('generateEventId')

const isLoading = ref(false)
async function search(val: string) {
  if (!val)
    visible.value = false

  if (isLoading.value || !generateEventId || !val)
    return

  isLoading.value = true
  visible.value = true
  list.value = []
  const res = await useAiGenSearch({ search: val, event_id: generateEventId.value })
  if (res.data.value?.result) {
    list.value = res.data.value.result.map((i) => {
      return {
        ...i,
        isHover: false,
      }
    })
  }

  isLoading.value = false
}

const card = ref()
const MAX_WORD_COUNT = 5000
onClickOutside(card, () => {
  visible.value = false
})
const isInputFocus = ref(false)
function handleInpunt(value_: string) {
  let value = value_
  if (countWordsDistinguishCE(value) > MAX_WORD_COUNT) {
    let end = MAX_WORD_COUNT
    value = value_.slice(0, end)
    while (countWordsDistinguishCE(value) < MAX_WORD_COUNT) {
      end += 1
      value = value_.slice(0, end)
    }
  }

  $emit('update:model-value', value)
}

watch(() => props.modelValue, (val, oldVale) => {
  if (val !== oldVale)
    handleInpunt(val)
}, { immediate: true })

function handleItemClick(item: { title: string; abstract: string; url: string }) {
  $emit('update:model-value', `${item.title}\n${item.abstract}`)
  const copy = structuredClone(toRaw(item))
  $emit('select', copy)
  visible.value = false
}

const visibleInput = ref(false)
async function handleBoxClick() {
  visibleInput.value = true
  await nextTick()
  input.value?.focus()
}
function handleBlur() {
  if (props.modelValue.trim().length === 0)
    visibleInput.value = false

  isInputFocus.value = false
}

function handleFocus() {
  isInputFocus.value = true
}

function handleItemMouseover(event: Event, item: { isHover: boolean }) {
  (event.target as HTMLElement)?.scrollIntoView({
    behavior: 'smooth',
    block: 'nearest',
    inline: 'nearest',
  })

  item.isHover = true
}

function handleEnter() {
  search(props.modelValue.trim())
  setTimeout(() => {
    popover.value.popperRef.popperInstanceRef.update()
  }, 100)
}

function goUrl(url: string) {
  window.open(url, '_blank')
}

function handleUploadResponse(res: string) {
  const text = `${props.modelValue} ${res}`
  if (countWordsDistinguishCE(text) > MAX_WORD_COUNT)
    ElMessage.warning('您上传的文档文字超过了5000字，系统已自动进行截取放入文本框中')

  handleInpunt(text)
}

const currentWordCount = computed(() => countWordsDistinguishCE(props.modelValue))
</script>

<template>
  <div class="relative">
    <div id="generate-event-box" class="event-box" :class="{ 'is-focus': isInputFocus }" @click="handleBoxClick">
      <div class="w-full h-[73px] overflow-y-auto" @scroll="visible = false">
        <el-popover
          ref="popover"
          :visible="visible"
          :show-arrow="false"
          width="406"
          :popper-style="{
            padding: 0,
            boxShadow: '0px 15px 30px rgba(0, 0, 0, 0.10)',
            borderRadius: '3px',
          }"
          placement="bottom"
        >
          <template #reference>
            <div class="relative">
              <div v-if="!isInputFocus && props.modelValue.length === 0" class="text-placehold absolute top-0 left-0 text-hidden-2">
                请输入您想评论的事件关键词，按回车通过互联网搜索，或手动输入事件全部信息
              </div>
              <!-- eslint-disable-next-line vue/no-deprecated-v-on-native-modifier -->
              <el-input ref="input" class="no-border" :model-value="props.modelValue" autosize type="textarea" @focus="handleFocus" @input="handleInpunt" @blur="handleBlur" @keyup.enter.native="handleEnter" />
            </div>
          </template>
          <template #default>
            <div ref="card" class="card">
              <p class="sticky top-0 bg-white flex items-center justify-between text1 text-[#AEB1B5] pt-[12px] px-[16px] pb-[12px]">
                <span>以下可能是你想要输入的事件信息</span>
                <span class="cursor-pointer" @click="visible = false">关闭</span>
              </p>
              <div class="list min-h-[200px]">
                <template v-if="!isLoading">
                  <div
                    v-for="(item, index) in list"
                    :key="index"
                    class="item"
                    :class="{
                      'is-hover': item.isHover,
                    }"
                    @click="handleItemClick(item)"
                    @mouseover="handleItemMouseover($event, item)"
                  >
                    <p class="tex1 text-n1-color px-[16px] truncate">
                      {{ item.title }}
                    </p>
                    <p class="text2 text-[#474E58] mt-[8px] px-[16px] mb-[12px] text-hidden-2 h-[44px]">
                      {{ item.abstract }}
                      <span class="text-[#4044ED] cursor-pointer text-[12px]" @click.stop="goUrl(item.url)">查看详情</span>
                    </p>
                  </div>
                </template>
                <div v-if="isLoading" class="flex items-center justify-center h-[200px] w-full">
                  <DocLoading :width="30" :hidde-text="true" />
                </div>
                <div v-if="(list.length === 0) && !isLoading" class="flex items-center justify-center h-[200px] w-full">
                  搜索失败，建议换一个关键词回车发起搜索
                </div>
              </div>
            </div>
          </template>
        </el-popover>
      </div>
    </div>
    <div class="absolute bottom-[4px] right-[25px] left-[16px] flex items-center justify-between">
      <Upload @response="handleUploadResponse" />
      <div />
      <div class="text3">
        <span class="mr-[8px] text-[#AEB1B5]">按回车开始搜索</span>
        <span
          :class="{
            'text-[#4044ED]': currentWordCount < MAX_WORD_COUNT,
            'text-[#EC1D13]': currentWordCount >= MAX_WORD_COUNT,
          }"
        >
          {{ currentWordCount }}
        </span>
        <span class=" text-n1-color">/{{ MAX_WORD_COUNT }}</span>
      </div>
    </div>
    <div class="absolute bottom-[-16px] text-[12px] text-[#EC1D13] hidden error-text">
      评论事件至少输入10个字哦
    </div>
  </div>
  <div v-if="props.currentUrl" class="w-full mt-[6px]">
    <div class="link-contianer flex justify-between items-center">
      <div class="truncate mr-[8px]">
        <NuxtLink class="link" :href="props.currentUrl" target="_blank">
          {{ props.currentUrl }}
        </NuxtLink>
      </div>
      <div class="rounded-full shrink-0 bg-[#7c7d7e] w-[12px] h-[12px] flex items-center justify-center cursor-pointer" @click="$emit('update:currentUrl', '')">
        <div class="i-ll-close text-[10px] text-white" />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.event-box {
  &:deep( textarea) {
    border: none;
    outline: none;
    background: none;
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px;
    color: var(--N1, #19222E);
    box-shadow: none;
    border-radius: 0;
    padding: 0;
    resize: none;
  }
}

.event-box {
    margin-top: 16px;
    overflow: hidden;
    width: 437px;
    height: 114px;
    border-radius: 5px;
    border: 1px solid var(--N6, #D2D4D6);
    padding: 10px 16px;
    padding-bottom: 22px;
    &:not(.is-focus):hover {
      border: 1px solid var(--N1, #19222E);
    }

    &:deep(.el-textarea__inner:hover) {
      box-shadow: none !important;
    }
}

.is-error {
  .event-box {
    border: 1px solid #EC1D13 !important;
  }

  .error-text {
    display: block !important;
  }

}

.is-focus {
  border-radius: 3px;
  border-style: solid;
  border-width: 2px;
  border-image: linear-gradient(to right, rgba(164, 149, 255, 1), rgba(40, 62, 255, 1), rgba(219, 50, 222, 1), rgba(64, 68, 237, 1), rgba(54, 38, 153, 1)) 1;
}

.card {
  max-height: 325px;
  overflow-y: auto;

  &::-webkit-scrollbar {
    width: 3px;
  }
}

.text1 {
  font-size: 14px;
  font-style: normal;
  font-weight: 700;
  line-height: 22px;
}

.text2 {
  font-size: 14px;
  font-style: normal;
  font-weight: 400;
  line-height: 22px;
}

.text3 {
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  line-height: 22px;
}

.item {
  width: 100%;
  border-bottom: 1px solid #DFE1E2;
  cursor: pointer;
  margin-top: 12px;

  &:first-child {
    margin-top: 0;
  }

  &:last-child {
    border-bottom: none;
  }

  &.is-hover p {
    overflow:visible !important;
    white-space: normal !important;
    text-overflow: initial !important;
    height: auto !important;
    display: block !important;
  }
}

.text-placehold {
  font-size: 14px;
  line-height: 22px;
  font-weight: 350;
  color: rgb(216, 216, 216);
  pointer-events: none;
}

.link-contianer {
  background-color: rgb(238, 237, 237);
  border-radius: 5px;
  font-size: 12px;
  color: var(--N1);
  padding: 4px 8px 4px 8px;
  max-width: 437px;
  opacity: 0.7;
}
</style>
