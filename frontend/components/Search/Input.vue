<script setup lang="ts">
import { QaMode } from '~/store/qa'

const props = defineProps<{
  options: { type: string; value: string; id: string }[]
  modelValue: string
  state: 'normal' | 'error' | 'empty'
  fullScreen: boolean
  isPro: boolean
  searchMode: string
}>()

const $emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'update:fullScreen', value: boolean): void
  (e: 'update:isPro', value: boolean): void
  (e: 'delete', value: string): void
  (e: 'clearAll'): void
  (e: 'ask'): void
  (e: 'search', value: string): void
  (e: 'focus', value: boolean): void
  (e: 'outside'): void
}>()

const { fullScreen, state } = toRefs(props)

const lastestInputValue = ref('')

function handleInput(value: string) {
  lastestInputValue.value = value
  $emit('update:modelValue', value)
  $emit('search', value)
}

const isFocus = ref(false)

const filteredOptions = computed(() => {
  if (!isFocus.value)
    return []
  return props.options
})

function handleDelete(id: string) {
  $emit('delete', id)
}

function handleClearAll() {
  $emit('clearAll')
}

const inputRef = ref()
function handleContainerClickCapture() {
  inputRef.value.focus()
}

const containerRef = ref()
onClickOutside(containerRef, () => {
  isFocus.value = false
  $emit('outside')
})

function handleEnter(e: KeyboardEvent | Event) {
  if ((e as KeyboardEvent).isComposing)
    return

  if ((e as KeyboardEvent).shiftKey) {
    handleInput(`${props.modelValue}\n`)
    return
  }

  $emit('ask')
}

const selectedValue = ref('')
const activeIndex = computed(() => {
  return filteredOptions.value.findIndex(item => item.id === selectedValue.value)
})
const open = computed(() => {
  if (filteredOptions.value.length === 0)
    return false

  if (fullScreen.value)
    return false

  return true
})

watch(open, (value) => {
  if (!value)
    selectedValue.value = ''
})

function handleKeyDown(ev: KeyboardEvent | Event) {
  if (!open.value)
    return

  let val = ''
  if ((ev as KeyboardEvent).key === 'ArrowUp')
    val = 'up'
  else
    val = 'down'

  const index = activeIndex.value
  if ((index === 0 && val === 'up')) {
    handleSelect('')
    return
  }
  if (index === (filteredOptions.value.length - 1) && val === 'down') {
    handleSelect(filteredOptions.value[0].id)
    return
  }

  if ((index === -1 && filteredOptions.value.length)) {
    handleSelect(filteredOptions.value[0].id)
  }
  else {
    const index_ = val === 'up' ? index - 1 : index + 1
    handleSelect(filteredOptions.value[index_].id)
  }
}

function handleSelect(id: string) {
  const val = filteredOptions.value.find(item => item.id === id)?.value || ''
  if (val === '')
    $emit('update:modelValue', lastestInputValue.value)
  else
    $emit('update:modelValue', val)

  selectedValue.value = id
}

function handleFocus() {
  isFocus.value = true
  $emit('focus', true)
}

const borderColor = computed(() => {
  return {
    '!border-[#4044ED]': state.value === 'normal',
    '!border-[#D54941]': state.value === 'error',
  }
})

const inputContainerRef = ref()
const maxRows = ref(13)
useResizeObserver(inputContainerRef, (entries) => {
  const entry = entries[0]
  const { height } = entry.contentRect
  const rows = Math.floor((height - 32) / 21)
  if (rows > 13)
    maxRows.value = rows
})
const textareaAutoSize = computed(() => {
  return {
    minRows: props.searchMode === QaMode.WEB ? 2 : 1,
    maxRows: maxRows.value,
  }
})
watch(() => props.fullScreen, (value) => {
  if (!value)
    maxRows.value = 13
})

watch(maxRows, () => {
  nextTick(() => {
    inputRef.value.resizeTextarea()
  })
})

watch(() => props.searchMode, () => {
  inputContainerRef.value.focus()
})

function handleOptionClick(id: string) {
  handleSelect(id)
  $emit('ask')
}

const fontCount = computed(() => {
  const current = props.modelValue.trim().length
  if (current > 10000)
    return '问题不能超过1万字，请删减字数'
  if (!fullScreen.value)
    return ''
  return `还可输入 ${10000 - current} 字，已输入 ${current} 字`
})

function handleSearchModel(value: boolean) {
  $emit('update:isPro', value)
}
</script>

<template>
  <div
    id="search-input-container"
    ref="containerRef"
    :class="{
      relative: !fullScreen,
    }"
    @click="handleContainerClickCapture"
  >
    <div v-if="fullScreen" class="w-[700px] h-[332.33px]" />

    <div
      ref="inputContainerRef"
      class="flex flex-col justify-between rounded-[12px] border py-[12px] input-contianer bg-white border-[rgba(0,0,0,0.15)]"
      :class="{
        'max-h-[342px]': !fullScreen,
        'w-[700px]': !fullScreen,
        'border-b-0': open,
        'rounded-b-none': open,
        'absolute': fullScreen,
        'top-[24px]': fullScreen,
        'left-[24px]': fullScreen,
        'right-[24px]': fullScreen,
        'z-10': fullScreen,
        'bottom-[24px]': fullScreen,
        'is-open': open,
        ...borderColor,
      }"
    >
      <el-input
        ref="inputRef"
        :model-value="props.modelValue"
        :autosize="textareaAutoSize"
        type="textarea"
        placeholder="尽管输入任何您想了解的事件~"
        @input="handleInput"
        @focus="handleFocus"
        @keydown.enter.prevent="handleEnter"
        @keydown.down.up.prevent="handleKeyDown"
      />
      <div class="flex items-center justify-between px-[12px] w-full pt-[8px]">
        <div class="flex items-center">
          <span
            class="text-[12px] font-normal leading-normal text-[rgba(0,0,0,0.45)]"
            :class="{
              '!text-[#D54941]': props.modelValue.trim().length > 10000,
            }"
          >{{ fontCount }}</span>
        </div>
        <div class="flex items-center">
          <template v-if="$props.searchMode === QaMode.WEB">
            <SearchSwitch :model-value="props.isPro" @update:model-value="handleSearchModel" />
          </template>
          <button
            v-if="props.modelValue.trim().length > 50 || fullScreen"
            :aria-label="fullScreen ? 'Fullscreen search box' : 'Exit full screen in search box'"
            class="px-0 cursor-pointer ml-[8px]"
            @click="$emit('update:fullScreen', !fullScreen)"
          >
            <div
              class="bg-[#F1F1F1] hover:bg-[#E7E7E7] rounded-full w-[23px] h-[23px] flex items-center justify-center"
            >
              <div
                :class="{
                  'i-ll-fold-fullscreen': fullScreen,
                  'i-ll-unfold-fullscreen': !fullScreen,
                }"
                class="text-[12px] text-[rgba(0,0,0,0.4)] hover:text-[rgba(0,0,0,0.6)]"
              />
            </div>
          </button>
          <button aria-label="Search question" class="px-0  ml-[8px] cursor-pointer" @click="$emit('ask')">
            <div
              class="i-ll-send text-[23px] text-[#D8D8D8]"
              :class="{
                '!text-[#4044ED]': state === 'normal',
                '!text-[#D54941]': state === 'error',
              }"
            />
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="open"
      class="w-full px-[12px] border border-y-none"
      :class="borderColor"
    >
      <div class="border-b border-[#D9D9D9]" />
    </div>
    <div
      v-if="open"
      class="border rounded-lg border-t-0 rounded-t-none px-[8px] py-[8px] absolute z-10 left-0 right-0 max-h-[240px] overflow-y-scroll bg-white is-open-bottom"
      :class="borderColor"
      role="listbox"
    >
      <div
        v-for="item in filteredOptions"
        :key="item.id"
        class="hover:bg-[#F3F3F3] cursor-pointer option-container rounded-[3px] px-[8px] py-[7px] w-full"
        role="option"
        :data-highlighted="item.id === selectedValue"
        @click="handleOptionClick(item.id)"
      >
        <div
          class="w-full flex items-center justify-between hover:text-[rgba(0,0,0,0.9)]"
          :class="{
            'text-[rgba(0,0,0,0.9)]': item.id === selectedValue,
            'text-[rgba(0,0,0,0.6)]': item.id !== selectedValue,
          }"
        >
          <SearchOptionContent :value="item.value" :diff-value="props.modelValue" />
          <div
            v-if="item.type === 'history'"
            class="i-ll-logo-dustbin text-[16px] btn-delete cursor-pointer shrink-0"
            @click.stop="handleDelete(item.id)"
          />
        </div>
      </div>
      <div v-if="filteredOptions[0] && filteredOptions[0].type === 'history'" class="flex items-center justify-end pt-[2px]">
        <div class="flex items-center cursor-pointer" @click.stop="handleClearAll">
          <div class="i-ll-logo-dustbin text-[14px] text-[rgba(0,0,0,0.6)] mr-[4px]" />
          <div class="text-[rgba(0,0,0,0.6)] text-[14px] leading-[22px]">
            清空历史记录
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.input-contianer:deep(.el-textarea__inner)  {
  box-shadow: none !important;
  padding: 0;
  background: transparent;
}
.input-contianer:deep(textarea) {
  color: rgba(0, 0, 0, 0.9);
  resize: none;
  padding: 0px 12px !important;
}

.option-container:hover {
  .btn-delete {
    display: block;
  }
}

.btn-delete {
  display: none;
}

[data-highlighted=true] {
  .btn-delete {
    display: block;
  }

  background-color: #F3F3F3;
}

.is-open {
  box-shadow: 0px 6px 16px 0px rgba(0, 0, 0, 0.08),0px 3px 6px -4px rgba(0, 0, 0, 0.12),0px 9px 28px 8px rgba(0, 0, 0, 0.05)
}

.is-open-bottom {
  box-shadow: 0px 6px 6px 0px rgba(0, 0, 0, 0.08),0px 3px 3px -4px rgba(0, 0, 0, 0.12),0px 9px 9px 8px rgba(0, 0, 0, 0.05)
}
</style>
