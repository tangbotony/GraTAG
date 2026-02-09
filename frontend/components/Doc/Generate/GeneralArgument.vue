<script setup lang="ts">
const props = defineProps<{
  data: { text: string; isUp: boolean; isDown: boolean; originText: string }[][]
}>()
const { data } = toRefs(props)
const isLoadingGeneralArgument = inject<Ref<boolean>>('isLoadingGeneralArgument')

const currentIndex = inject<Ref<number>>('currentGeneralIndex')
const selectedIndex = inject<Ref<string>>('currentGeneralSelectedIndex')
const generalArgument = inject<Ref<{ argument: string; argumentFix: string }>>('generalArgument')
const currentData = computed(() => {
  return data.value[currentIndex!.value] || []
})

function before() {
  if (currentIndex?.value === undefined)
    return

  if (currentIndex.value <= 0)
    return

  currentIndex.value -= 1
}

function after() {
  if (currentIndex?.value === undefined)
    return

  if (currentIndex.value === data.value.length - 1)
    return

  currentIndex.value += 1
}

const currentEditIndex = ref('')
const inputValue = ref('')
const inputRef = ref()
async function handleEdit(val: string, item: { text: string }) {
  inputValue.value = item.text
  currentEditIndex.value = val
  await nextTick()
  inputRef.value?.[0]?.focus()
}

function cancel() {
  currentEditIndex.value = ''
  inputValue.value = ''
}

function ok(item: { text: string }, index: string) {
  currentEditIndex.value = ''
  item.text = inputValue.value.trim().replaceAll('\n', '')
  if (index === selectedIndex?.value) {
    if (generalArgument?.value)
      generalArgument.value.argumentFix = inputValue.value.trim().replaceAll('\n', '')
  }
  inputValue.value = ''
}

const reqController = inject<Ref<AbortController>>('reqController')!

function cancelReq() {
  reqController.value?.abort()
}
</script>

<template>
  <div class="list">
    <template v-if="isLoadingGeneralArgument">
      <div class="w-full h-[250px] flex items-center justify-center">
        <DocLoading :duration="30" @cancle="cancelReq" />
      </div>
    </template>
    <template v-else-if="currentData.length > 0">
      <div
        v-for="(item, index) in currentData"
        :key="`${currentIndex},${index}`"
        class="py-[16px] rounded-[10px] box-border relative bg-[#F8F8F8] mb-[16px]"
        :class="{
          'is-selected': (selectedIndex === `${currentIndex},${index}`),
        }"
        @click="selectedIndex = `${currentIndex},${index}`"
      >
        <div class="px-[24px] text-[14px] leading-[22px] text-black-color item-argument relative">
          <div class="whitespace-pre-wrap" v-html="item.text" />
          <template v-if="currentEditIndex === `${currentIndex},${index}`">
            <div class="absolute top-[-16px] left-0 bottom-[-48px] right-0 bg-white edit-box z-10 flex flex-col">
              <div class="flex-1 overflow-y-auto">
                <el-input ref="inputRef" v-model="inputValue" autosize type="textarea" maxlength="500" autofocus />
              </div>
              <div class="flex items-center justify-end mt-[8px] shrink-0">
                <el-button size="small" @click="cancel">
                  取消
                </el-button>
                <el-button size="small" type="primary" @click="ok(item, `${currentIndex},${index}`)">
                  确认
                </el-button>
              </div>
            </div>
          </template>
        </div>
        <div v-if="selectedIndex === `${currentIndex},${index}`" class="px-[24px] flex items-center mt-[8px] justify-between h-[24px]">
          <div class="flex items-center">
            <div class="btn mr-[8px] flex items-center cursor-pointer" @click="handleEdit(`${currentIndex},${index}`, item)">
              <div class="i-ll-edit text-[14px]" />
              <span class="text-[12px] ml-[4px]">编辑</span>
            </div>
          </div>
          <DownUpIcon />
        </div>
      </div>
    </template>

    <div v-if="data.length > 1 && currentIndex !== undefined && currentIndex !== -1" class="absolute right-[18px] bottom-[-60px] flex items-center">
      <div class="i-ll-arrow-left text-[14px] origin-center cursor-pointer" @click="before" />
      <div class="text1">
        <span class="text-[#4044ED]">{{ currentIndex + 1 }}</span>
        <span>/{{ data.length }}</span>
      </div>
      <div class="i-ll-arrow-left rotate-180 text-[14px] cursor-pointer" @click="after" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.option:deep(.el-radio) {
    margin: 0 !important;
    height: auto !important;
    padding-top: 3px;
}

.option {
  margin-bottom: 26px;
}
.list .item:last-child {
  margin-bottom: 0px;
  position: relative;
}

.text2 {
    color: var(--N2, #474E58);
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px;
}

.text1 {
    color: var(--N1, #19222E);
    font-size: 14px;
    font-style: normal;
    font-weight: 600;
    line-height: 22px;
}

.text3 {
    color: var(--N1, #19222E);
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px;
}

.argument-text:hover {
  display: block !important;
}

.is-selected:before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 10px;
  border: 2px solid #4044ED;
  pointer-events: none;
}

.btn {
    padding: 0 8px;
    border-radius: 4px;
    cursor: pointer;
    color: rgba(0, 0, 0, 0.36);
    &:hover {
        color: var(--c-text-black);
        background: #F1F1F1;
    }
}

.item-argument {
  &:deep( textarea) {
    border: none;
    outline: none;
    background: none;
    box-shadow: none;
    border-radius: 0;
    padding: 0;
    resize: none;
    font-size: 14px;
    line-height: 22px;
  }
}

.edit-box {
  border-radius: 5px;
  padding: 16px 24px;
  box-shadow: 0px 0px 10px 0px rgba(25, 34, 46, 0.16);
}
</style>
