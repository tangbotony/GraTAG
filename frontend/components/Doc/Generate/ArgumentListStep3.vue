<script setup lang="ts">
import { driver } from 'driver.js'
import type { ArgumentType } from '~/composables/ai/generate'

const props = defineProps<{
  data: ArgumentType[][]
  state: {
    currentIndex: number
    selectedIndex: string[]
  }
  generateArgumentRefresh: (val?: string) => Promise<boolean | undefined>
}>()

const $emits = defineEmits<{
  (e: 'generateEvidence', value: [number, number] | [number, number, number]): void
  (e: 'cancelRequest'): void
  (e: 'clearEmptyEvidence'): void
}>()

const { data, state } = toRefs(props)
const boxAdd = ref()
const visiblueAdd = ref(false)
const visibleOverlay = ref(false)
const isLoadingGenerateArguments = inject<Ref<boolean>>('isLoadingGenerateArguments')!
const loadingEvidenceSelectedIndex = inject<Ref<string[]>>('loadingEvidenceSelectedIndex')!
const controllerEvidence = inject<Ref<{ control: AbortController; index: string }[]>>('controllerEvidence')!
const isLoadingGenerateArgumentsIndex = inject<Ref<number>>('isLoadingGenerateArgumentsIndex')!
onClickOutside(boxAdd, () => {
  visiblueAdd.value = false
  visibleOverlay.value = false
})

const currentIndex = computed({
  get() {
    return state.value.currentIndex
  },
  set(val) {
    state.value.currentIndex = val
  },
})

const selectedIndex = computed({
  get() {
    return state.value.selectedIndex
  },
  set(val) {
    state.value.selectedIndex = val
  },
})

const currentData = computed(() => {
  return data.value[currentIndex.value] || []
})

function before() {
  if (currentIndex.value <= 0)
    return

  currentIndex.value -= 1
}

function after() {
  if (currentIndex.value === data.value.length - 1)
    return

  currentIndex.value += 1
}

function handleCheckChange(value: boolean, pos: string) {
  if (value) {
    if (selectedIndex.value.length >= 10) {
      ElMessage.error('最多只能采纳10个论点')
      return
    }
    selectedIndex.value.push(pos)
  }
  else { selectedIndex.value.splice(selectedIndex.value.indexOf(pos), 1) }
}

// const sum = computed(() => {
//   return data.value.reduce((acc, cur) => {
//     return acc + cur.length
//   }, 0)
// })

// const isCheckAll = computed(() => {
//   if (!selectedIndex.value || selectedIndex.value.length === 0)
//     return false
//   return selectedIndex.value.length === sum.value
// })
// const isIndeterminate = computed(() => {
//   return (selectedIndex.value.length !== sum.value) && (selectedIndex.value.length !== 0)
// })

// function handleCheckAllChange(val: boolean) {
//   if (val) {
//     const sum = data.value.reduce((acc, cur) => {
//       return acc + cur.length
//     }, 0)
//     if (sum >= 10) {
//       ElMessage.error('最多只能采纳10个论点')
//       return
//     }

//     selectedIndex.value = data.value.reduce((acc, cur, index) => {
//       return acc.concat(cur.map((_, i) => `${index},${i}`))
//     }, [] as string[])
//   }

//   else { selectedIndex.value = [] }
// }

const popverInstance = ref()
provide('popverInstance', popverInstance)

const argument = ref('')
const userArgumentsCount = computed(() => {
  return data.value.reduce((acc, cur) => {
    return acc + cur.filter(item => item.isUser).length
  }, 0)
})
function handleVisiblueAdd() {
  if (isLoadingGenerateArguments.value)
    return

  popverInstance.value?.exposed.hide()
  argument.value = ''
  visiblueAdd.value = true
  visibleOverlay.value = true
}

function addArgument() {
  currentData.value.push({
    argument: argument.value,
    evidence: [],
    evidenceIndex: -1,
    isArgumentDown: false,
    isArgumentUp: false,
    isUser: true,
    reference_index: -1,
  })
  argument.value = ''
  visiblueAdd.value = false
  visibleOverlay.value = false
  $emits('generateEvidence', [currentIndex.value, currentData.value.length - 1, -1])
}

function cancelAddArgument() {
  visiblueAdd.value = false
  visibleOverlay.value = false
}

function handleRefresh(index: number) {
  $emits('generateEvidence', [currentIndex.value, index])
}

function beforeEvidence(item: any) {
  if (item.evidenceIndex === 0)
    return

  item.evidenceIndex = item.evidenceIndex - 1
}

function afterEvidence(item: any) {
  if (item.evidenceIndex === item.evidence.length - 1)
    return

  item.evidenceIndex = item.evidenceIndex + 1
}

const generateContainer = inject<Ref<HTMLElement>>('generateContainer')!

const { isScrolling } = useScroll(generateContainer)
watch(isScrolling, (val) => {
  if (val)
    popverInstance.value?.exposed.hide()
})

function cancelReq() {
  $emits('cancelRequest')
}

function handleEvidenceCancel(pos: string) {
  const index = controllerEvidence.value.findIndex(item => item.index === pos)
  if (index > -1) {
    controllerEvidence.value[index].control.abort()
    controllerEvidence.value.splice(index, 1)
  }
}

const isStep3Init = inject<Ref<boolean>>('isStep3Init')!
watch(isStep3Init, async (val) => {
  if (!val)
    return

  if (currentUser.value?.extend_data?.generate_step_3)
    return

  updateUserInfo('generate_step_3', true)
  generateContainer.value?.scrollTo({
    top: 70,
    behavior: 'smooth',
  })
  await sleep(500)
  const driverObj = driver({
    showProgress: true,
    showButtons: ['next'],
    nextBtnText: '下一步',
    doneBtnText: '完成',
    progressText: '{{current}}/{{total}}',
    steps: [
      { element: '#generate-step3-item1', popover: { description: '勾选即代表采纳这组论点/论据了哦' } },
      { element: '#generate-step3-item1-argument', popover: { description: '单击论点，即可唤起操作气泡哦' } },
      { element: '#generate-step3-item1-evidence', popover: { description: '单击论据，即可唤起操作气泡哦' } },
    ],
    onPopoverRender: (popover, options) => {
      if (options.state.activeIndex === 1 || options.state.activeIndex === 2) {
        const item = options.state.activeElement?.querySelector('.item')

        if (!item)
          return

        const rect = item.getBoundingClientRect()
        const centerX = rect.left + rect.width / 2
        let centerY = rect.top
        if (options.state.activeIndex === 2)
          centerY = rect.top + rect.height / 2
        else
          centerY = rect.top + rect.height + 23
        item.dispatchEvent(new MouseEvent('click', { clientX: centerX, clientY: centerY }))
      }
    },
  })
  driverObj.drive()
}, { deep: true })

const isGenerateArgumentRefresh = ref(false)

async function submitGenerateArgumentRefresh(val?: string) {
  if (isGenerateArgumentRefresh.value)
    return

  isGenerateArgumentRefresh.value = true
  const res = await props.generateArgumentRefresh(val)
  if (!res)
    $emits('clearEmptyEvidence')

  isGenerateArgumentRefresh.value = false
}

const loadingData = computed(() => {
  const d = data.value[isLoadingGenerateArgumentsIndex.value]?.filter((item) => {
    return item.evidence.length > 0
  })
  return d || []
})

const currentCompleteData = computed(() => {
  return currentData.value.filter((item) => {
    return !(!item.isUser && item.evidence.length === 0)
  })
})
</script>

<template>
  <template v-if="isLoadingGenerateArguments && loadingData.length === 0">
    <div class="w-full h-[250px] flex items-center justify-center">
      <DocLoading :duration="30" @cancle="cancelReq" />
    </div>
  </template>
  <template v-else>
    <div class="relative">
      <div class="min-h-[66px]">
        <div
          v-for="(item, index) in currentCompleteData"
          :id="index === 0 ? 'generate-step3-item1' : ''"
          :key="index"
          class="flex items-start option mb-[9px] flex-col px-[25px] py-[10px] relative"
          :class="{
            'is-selected': selectedIndex.includes(`${currentIndex},${index}`),
          }"
        >
          <div :id="index === 0 ? 'generate-step3-item1-argument' : ''" class="flex items-start relative check-container mb-[5px] w-full">
            <div class="absolute top-[4px] left-0">
              <el-checkbox
                :model-value="selectedIndex.includes(`${currentIndex},${index}`)"
                :label="`${currentIndex},${index}`"
                size="large"
                @update:model-value="handleCheckChange(($event as boolean), `${currentIndex},${index}`)"
              >
                <div />
              </el-checkbox>
            </div>
            <DocGenerateArgumentPopover
              v-model:text="item.argument"
              v-model:is-down="item.isArgumentDown"
              v-model:is-up="item.isArgumentUp"
              :maxlength="500"
              width="max-content"
              placement="top"
              @show="visibleOverlay = true"
              @hide="visibleOverlay = false"
            >
              <template #reference>
                <div
                  class="indent-[20px] text1 w-full whitespace-pre-wrap"
                  v-html="`论点${index + 1}: ${item.argument}`"
                />
              </template>
            </DocGenerateArgumentPopover>
          </div>

          <div v-if="loadingEvidenceSelectedIndex?.includes(`${currentIndex},${index}`) && item.evidence.length > 0" class="w-full h-[60px] mt-[18px] flex items-center justify-center">
            <DocLoading :duration="15" :width="32" @cancle="handleEvidenceCancel(`${currentIndex},${index}`)" />
          </div>
          <div v-else-if="loadingEvidenceSelectedIndex?.includes(`${currentIndex},${index}`) && item.evidence.length === 0" class="w-full h-[60px] mt-[18px] flex items-center justify-center">
            <DocLoading :duration="30" :width="32" :disable-cancel="true" />
          </div>
          <template v-else>
            <div :id="index === 0 ? 'generate-step3-item1-evidence' : ''" class="flex items-center">
              <DocGenerateArgumentPopover
                v-if="item.evidence[item.evidenceIndex]"
                v-model:text="item.evidence[item.evidenceIndex].text"
                v-model:is-down="item.evidence[item.evidenceIndex].isDown"
                v-model:is-up="item.evidence[item.evidenceIndex].isUp"
                :maxlength="500"
                placement="top"
                width="max-content"
                @show="visibleOverlay = true"
                @hide="visibleOverlay = false"
              >
                <template #reference>
                  <div
                    class="w-full text2 min-h-[66px] whitespace-pre-wrap"
                    v-html="item.evidence[item.evidenceIndex].text"
                  />
                </template>
                <template #default>
                  <div v-if="item.evidence.length > 1" class="flex items-center ml-[16px]">
                    <div class="i-ll-arrow-left text-[14px] origin-center cursor-pointer" @click="beforeEvidence(item)" />
                    <div class="text3">
                      <span class="text-[#4044ED]">{{ item.evidenceIndex + 1 }}</span>
                      <span>/{{ item.evidence.length }}</span>
                    </div>
                    <div class="i-ll-arrow-left rotate-180 text-[14px] cursor-pointer" @click="afterEvidence(item)" />
                  </div>
                  <span class="cursor-pointer ml-[16px] inline-block" @click="handleRefresh(index)">点此换论据</span>
                </template>
              </DocGenerateArgumentPopover>
            </div>
          </template>
        </div>
        <div v-if="isLoadingGenerateArguments && loadingData.length > 0" class="w-full h-[80px] mt-[18px] flex items-center justify-center">
          <DocLoading :key="loadingData.length" :duration="15" :width="32" :disable-cancel="true" />
        </div>
      </div>
      <div v-if="visiblueAdd" class="px-[25px] mt-[22px]">
        <div ref="boxAdd" class="w-[400px] p-[8px] argument-add-box mb-[20px] relative z-100">
          <el-input
            v-model="argument"
            placeholder="请输入论点"
            type="textarea"
            :rows="3"
            style="width: 384px;"
            maxlength="500"
          />
          <div class="flex items-center justify-end mt-[8px]">
            <el-button size="small" @click="cancelAddArgument">
              取消
            </el-button>
            <el-button type="primary" size="small" @click="addArgument">
              确认
            </el-button>
          </div>
        </div>
      </div>
      <div v-if="visibleOverlay" class="absolute top-0 left-0 bottom-0 right-0 z-10" />
      <div v-if="userArgumentsCount < 10 && !isLoadingGenerateArguments" class="text4 flex items-center justify-center mb-[17px]">
        <div class="inline-block cursor-pointer" @click="handleVisiblueAdd">
          <span class="mr-[7px]">+</span>
          <span>手动新增论点</span>
        </div>
      </div>
    </div>
  </template>

  <div class="px-[18px] mt-[32px] mb-[128px] flex items-center justify-between">
    <div
      :class="{
        'pointer-events-none': isLoadingGenerateArguments || loadingEvidenceSelectedIndex.length > 0,
        'select-none': isLoadingGenerateArguments || loadingEvidenceSelectedIndex.length > 0,
      }"
    >
      <DocGenerateArgumentRefresh
        :data-length="data.length"
        @submit="submitGenerateArgumentRefresh"
      >
        <span v-if="isGenerateArgumentRefresh">
          重新生成中...
        </span>
        <span v-else>
          不满意？换一批论点
        </span>
      </DocGenerateArgumentRefresh>
    </div>
    <div class="flex items-center">
      <template v-if="data.length > 1 && !isGenerateArgumentRefresh">
        <div class="i-ll-arrow-left text-[14px] origin-center cursor-pointer" @click="before" />
        <div class="text3">
          <span class="text-[#4044ED]">{{ currentIndex + 1 }}</span>
          <span>/{{ data.length }}</span>
        </div>
        <div class="i-ll-arrow-left rotate-180 text-[14px] cursor-pointer" @click="after" />
      </template>
    </div>
  </div>

  <!--
      <div class="flex items-center text3">
        <el-checkbox
          :model-value="isCheckAll"
          :indeterminate="isIndeterminate"
          @update:model-value="handleCheckAllChange($event as boolean)"
        >
          <span />
        </el-checkbox>
        <span>已采纳</span>
        <span class="text-[#4044ED]">{{ selectedIndex.length }}个</span>
      </div> -->
</template>

<style lang="scss" scoped>
.text1 {
    color: var(--N1, #19222E);
    font-size: 14px;
    font-style: normal;
    font-weight: 600;
    line-height: 23px; /* 137.5% */
}

.text2 {
    color: var(--N2, #474E58);
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 23px;
}

.text3 {
    color: #19222E;
    font-size: 14px;
    font-style: normal;
    font-weight: 600;
    line-height: 22px; /* 157.143% */
}

.text4 {
    color: #4044ED;
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 21px;
}

.is-selected {
    background-color: #F9F9FE;
}

.check-container {
    &:deep(.el-checkbox.el-checkbox--large) {
        height: auto !important;
    }
}

.argument-add-box {
    border-radius: 3px;
    background: #FFF;
    box-shadow: 0px 0px 6px 0px rgba(0, 0, 0, 0.25);
}
</style>
