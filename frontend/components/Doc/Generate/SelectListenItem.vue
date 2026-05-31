<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'
import { driver } from 'driver.js'
import { useStep1, useStep2, useStep3 } from '~/composables/ai/generate'
import stats from '~/lib/stats'

const props = defineProps<{
  editor: Editor
  scrollContainer: any
}>()

const $emits = defineEmits<{
  (e: 'closed'): void
  (e: 'hide'): void
  (e: 'show'): void
}>()

const step = ref(1)
const eventId = ref(getRandomString())
provide('generateEventId', eventId)

const {
  event,
  eventCleared,
  eventTitle,
  eventAbstract,
  isEventError,
  writeStyle,
  userArguments,
  argumentPlaceholder,
  evidencePlaceholder,
  eventPlaceholder,
  handleEventSelect,
  clearStep1,
  isStep1Change,
  controller,
  userTitle,
  currentUrl,
} = useStep1(step, handleStep1Next)

const {
  generalArgument,
  structrue,
  generalArguments,
  isLoadingGeneralArgument,
  handleGeneralArgumentRefresh,
  clearStep2,
  isStep2Change,
  currentGeneralIndex,
  currentGeneralSelectedIndex,
} = useStep2(step, eventId, eventCleared,
  eventTitle, eventAbstract,
  userArguments, userTitle, handleStep2Next,
)

const container = ref()

const bodyGenArgument = computed(() => {
  return {
    event: eventCleared.value,
    title: eventTitle.value,
    user_title: userTitle.value,
    abstract: eventAbstract.value,
    generalArgument: generalArgument.value.argument,
    generalArgumentFix: generalArgument.value.argumentFix,
    arguments: userArguments.value.map((item) => {
      return {
        opinion: item.argument,
        evidence: item.evidence,
      }
    }),
  }
})

const {
  structrue3,
  generateArguments,
  generateArguments3,
  argumentsState,
  handleGenerateArgumentRefresh,
  generateEvidence,
  isLoadingGenerateArguments,
  clearStep3,
  generateArgumentsBody,
  generateArticle,
  controllerEvidence,
  loadingEvidenceSelectedIndex,
  isInit: isStep3Init,
  clearEmptyEvidence,
  generateArgumentRequestList,
  genArgumentHistory,
} = useStep3(step, eventId, bodyGenArgument)

const visibleStep4 = ref(false)
const step4Data = ref<any>()

function clearStep4() {
  visibleStep4.value = false
  step4Data.value = null
  props.editor.setEditable(true)
}

provide('reqController', controller)
provide('controllerEvidence', controllerEvidence)

watch([isLoadingGeneralArgument], (val) => {
  if (!val) {
    container.value?.scrollTo({
      top: 0,
      behavior: 'smooth',
    })
  }
})

async function handleStep1Next() {
  // gen gernal argument
  clearStep2()
  eventId.value = getRandomString()
  const result = await handleGeneralArgumentRefresh()
  if (!result) {
    step.value = 1
    isStep1Change.value = true
  }
  else {
    stats.track('text-generate', {
      action: 'generate',
      value: 1,
    })
  }
}

async function handleStep2Next() {
  clearStep3()
  structrue3.value = structrue.value
  const res = await handleGenerateArgumentRefresh()
  if (!res) {
    step.value = 2
    clearStep3()
    isStep2Change.value = true
  }
}

function next() {
  controller.value?.abort()

  if ((event.value.trim().length < 10) && step.value === 1) {
    isEventError.value = true
    return
  }

  const hasInvalidArgument = userArguments.value.some(i => i.argument.trim() === '' && i.evidence.trim().length > 0)
  if (hasInvalidArgument)
    return

  if (generalArgument.value.argumentFix.trim() === '' && step.value === 2) {
    ElMessage({
      message: '请选择总论点',
      type: 'warning',
      appendTo: container.value,
    })
    return
  }

  if (step.value === 3) {
    const isGen = generateArticle()
    if (isGen) {
      $emits('hide')
      step4Data.value = unref({
        ...bodyGenArgument.value,
        structrue: structrue3.value,
        event_id: eventId,
        generate_arguments: generateArgumentsBody.value,
        argument_history: genArgumentHistory(generateArguments.value),
      })
      visibleStep4.value = true
      props.editor.setEditable(false)
    }
    return
  }

  step.value += 1
}

function before() {
  clearReqController()
  step.value -= 1

  if (generalArgument.value.argumentFix === '')
    isStep1Change.value = true

  if (Object.keys(generateArgumentsBody).length === 0)
    isStep2Change.value = true
}

watch(isStep2Change, (val) => {
  if (val)
    clearStep3()
})

function clearReqController() {
  generateArgumentRequestList.value = []
  controller.value?.abort()
  controllerEvidence.value.forEach(c => c.control.abort())
  controllerEvidence.value = []
}

function cancelStep3Request() {
  clearReqController()
}

onMounted(async () => {
  await sleep(500)
  if (!currentUser.value?.extend_data?.generate_step_1) {
    const driverObj = driver({
      showProgress: true,
      showButtons: ['next'],
      nextBtnText: '下一步',
      doneBtnText: '完成',
      progressText: '{{current}}/{{total}}',
      steps: [
        {
          element: '#generate-event-box',
          popover: {
            description: `<div class="flex items-center" >
            <span>按下回车即可搜索您想评论的事件</span>
          </div>`,
          },
        },
        {
          element: '#generate-first-argument',
          popover: {
            description: `
          <div class="flex items-center" >
            <span>点击下方</span>
            <div class="driver-text-box mx-[6.5px]">
              输入框
            </div>
            <span>可以输入参考论点哦</span>
          </div>`,
          },
        },
      ],
      onDestroyed: (__, step, options) => {
        if (step.element === '#generate-first-argument') {
          container.value?.scrollTo({
            top: 0,
            behavior: 'smooth',
          })
        }
      },
      onHighlightStarted: (element) => {
        element?.scrollIntoView()
      },
    })
    driverObj.drive()
    updateUserInfo('generate_step_1', true)
  }
})

function clearAll() {
  clearReqController()
  clearStep1()
  clearStep2()
  clearStep3()
  clearStep4()
}

function close() {
  clearAll()
  $emits('closed')
}

function handleStructrueClicked() {
  ElMessage({
    type: 'error',
    message: '生成中不可切换',
  })
}

provide('generateContainer', container)

async function handleStructrue3Change(value: string) {
  const oldValue = structrue3.value
  structrue3.value = value
  if (generateArguments.value.length === 0) {
    const res = await handleGenerateArgumentRefresh()
    if (!res) {
      clearEmptyEvidence()
      structrue3.value = oldValue
    }
  }
}

function step4Apply() {
  visibleStep4.value = false
  close()
}

function step4Back() {
  visibleStep4.value = false
  $emits('show')
}

defineExpose({
  init: async () => {
  },
  clear: () => {
    clearAll()
  },
})
</script>

<template>
  <div ref="container" class="flex-1 overflow-y-auto w-full relative">
    <div class="sticky top-0 w-full flex items-center justify-between py-[21px] px-[16px] mb-[5px] bg-white z-10">
      <div class="flex items-center">
        <div class="i-custom:ai-ring w-[20px] h-[20px]" />
        <span class="text1">AI全文写作</span>
      </div>
      <div class="i-ll-close text-[20px] text-[#D9D9D9] mx-[8px] cursor-pointer" @click="close" />
    </div>
    <el-steps :active="step" align-center>
      <el-step>
        <template #title>
          <div>
            信息输入
          </div>
        </template>
      </el-step>

      <el-step>
        <template #title>
          <div>生成总论点</div>
        </template>
      </el-step>
      <el-step>
        <template #title>
          <div>
            生成论点/论据
          </div>
        </template>
      </el-step>
    </el-steps>
    <div v-if="step === 1">
      <div class="flex items-center justify-between mt-[36px] pl-[16px] pr-[24px]">
        <span class="text2 required">写作风格</span>
        <div class="w-[171px]">
          <el-select v-model="writeStyle" size="small">
            <el-option label="新华评论" value="xinhua" />
          </el-select>
        </div>
      </div>
      <p class="mt-[20px] px-[16px]">
        <span class="required text2">评论事件</span>
      </p>
      <div
        class="pl-[16px] relative"
        :class="{
          'is-error': isEventError,
        }"
      >
        <DocGenerateEventAutoComplete v-model="event" v-model:currentUrl="currentUrl" :placeholder="eventPlaceholder" @select="handleEventSelect" />
      </div>
      <p class="mt-[20px] px-[16px] text2">
        <span class="text2">参考标题</span><span class="text-[#8B9096]">（选填）</span>
      </p>
      <p class="mt-[12px] px-[16px] text2">
        <DocGenerateInput
          v-model="userTitle"
          :maxlength="50"
          placeholder="请输入您计划的评论标题"
        />
      </p>
      <p class="mt-[20px] px-[16px] text2">
        <span class="text2">参考论点/论据</span><span class="text-[#8B9096]">（选填）</span>
      </p>
      <p class="pl-[16px] mt-[12px]">
        <DocGenerateArgumentList :value="userArguments" :argument-placeholder="argumentPlaceholder" :evidence-placeholder="evidencePlaceholder" />
      </p>
    </div>
    <div v-if="step === 2">
      <div class="px-[18px] mt-[32px] min-h-[250px] bg-white relative mb-[30px]">
        <DocGenerateGeneralArgument :data="generalArguments" />
      </div>
      <div
        class="px-[18px]"
        :class="{
          'pointer-events-none': isLoadingGeneralArgument,
          'select-none': isLoadingGeneralArgument,
        }"
      >
        <DocGenerateArgumentRefresh
          :data-length="generalArguments.length"
          @submit="handleGeneralArgumentRefresh"
        >
          <span v-if="isLoadingGeneralArgument && generalArguments.length > 0">
            重新生成中...
          </span>
          <span v-else>
            不满意？点此换一批
          </span>
        </DocGenerateArgumentRefresh>
      </div>
      <p class="text3 mt-[26px] mb-[18px] px-[18px]">
        <span>期望论述结构</span>
        <span class="text-[#8B9096]">（选填）</span>
      </p>
      <p class="px-[18px] radio-group flex justify-start mb-[48px]">
        <el-radio-group v-model="structrue">
          <el-radio-button value="并列式" label="并列式">
            并列式
          </el-radio-button>
          <el-radio-button value="递进式" label="递进式">
            递进式
          </el-radio-button>
          <el-radio-button value="对比式" label="对比式">
            对比式
          </el-radio-button>
        </el-radio-group>
      </p>
    </div>
    <div v-if="step === 3">
      <div class="mt-[33px] pl-[18px] mb-[22px] radio-group flex justify-center relative">
        <div>
          <el-radio-group :model-value="structrue3" @update:model-value="(value: any) => { handleStructrue3Change(value) }">
            <el-radio-button value="并列式" label="并列式">
              并列式
            </el-radio-button>
            <el-radio-button value="递进式" label="递进式">
              递进式
            </el-radio-button>
            <el-radio-button value="对比式" label="对比式">
              对比式
            </el-radio-button>
          </el-radio-group>
        </div>
        <div v-if="isLoadingGenerateArguments" class="absolute top-0 bottom-0 left-0 right-0 z-10" @click="handleStructrueClicked" />
      </div>

      <DocGenerateArgumentListStep3
        :state="argumentsState"
        :data="generateArguments"
        :generate-argument-refresh="handleGenerateArgumentRefresh"
        @generate-evidence="generateEvidence"
        @cancel-request="cancelStep3Request"
        @clear-empty-evidence="clearEmptyEvidence"
      />
    </div>
  </div>
  <div class="h-[69px] border-t-1 w-full border-[rgba(217, 217, 217, 1)] flex items-center justify-end px-[24px]">
    <div
      v-if="step !== 1"
      class="w-[100px] h-[36px] mr-[12px] text1 flex items-center justify-center cursor-pointer border-1 border-[#DFE1E2] rounded-[100px]"
      @click="before"
    >
      <span>
        上一步
      </span>
    </div>
    <div class="btn-bottom-container flex">
      <div
        class="px-[11px] py-[7px] text1 flex items-center justify-center btn-bottom cursor-pointer"
        :class="{
          'pointer-events-none': isLoadingGeneralArgument || isLoadingGenerateArguments,
          'select-none': isLoadingGeneralArgument || isLoadingGenerateArguments,
        }"
        @click="next"
      >
        <span class="text-[#4044ED]">
          <template v-if="step === 1">
            下一步：生成总论点
          </template>
          <template v-else-if="step === 2">
            下一步：生成论点/论据
          </template>
          <template v-else-if="step === 3">
            下一步：生成全文
          </template>
        </span>
      </div>
    </div>
  </div>

  <DocGenerateStep4
    v-if="visibleStep4"
    :editor="props.editor"
    :scroll-container="scrollContainer"
    :data="step4Data"
    @apply="step4Apply"
    @back="step4Back"
  />
</template>

<style lang="scss" scoped>
.text1 {
    color: var(--N1, #19222E);
    font-size: 14px;
    font-style: normal;
    font-weight: 600;
    line-height: 22px;
}

.text2 {
    color: var(--N1, #19222E);
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px;
}

.required:after {
    content: "*";
    color: #F00;
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px;
    vertical-align: middle;
}

.btn-bottom-container {
  background: linear-gradient(to bottom right, #A495FF 0%, #A495FF 0%, #283EFF 25%, #DB32DE 50%, #4044ED 77%, #362699 100%, #362699 100%) bottom right, linear-gradient(to bottom left, #A495FF 0%, #A495FF 0%, #283EFF 25%, #DB32DE 50%, #4044ED 77%, #362699 100%, #362699 100%) bottom left, linear-gradient(to top left, #A495FF 0%, #A495FF 0%, #283EFF 25%, #DB32DE 50%, #4044ED 77%, #362699 100%, #362699 100%) top left, linear-gradient(to top right, #A495FF 0%, #A495FF 0%, #283EFF 25%, #DB32DE 50%, #4044ED 77%, #362699 100%, #362699 100%) top right;
  padding: 1px;
  border-radius: 100px;
}

.btn-bottom {
  background-color: white;
  border-radius: 100px;
}

.radio-group {
  &:deep(.is-active .el-radio-button__inner) {
    background: linear-gradient(270deg, #3D6EE2 0%, #2849E6 43.52%) !important;
  }
  &:deep( .el-radio-button__inner) {
    padding: 3px 31px;
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px;
  }
}
</style>
