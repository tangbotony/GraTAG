<script lang="ts" setup>
const props = defineProps<{
  dataLength: number
}>()
const $emits = defineEmits<{
  (e: 'submit', value?: string): void
}>()

const feedback = ref('')
const visiblePopover = ref(false)
const clickCount = ref(0)

const isLoadingGeneralArgument = inject<Ref<boolean>>('isLoadingGeneralArgument')
const isLoadingGenerateArguments = inject<Ref<boolean>>('isLoadingGenerateArguments')

function handleRefresh() {
  clickCount.value += 1
  if (clickCount.value >= 2)
    visiblePopover.value = true

  else
    $emits('submit')
}
const warn = ref('')
const messageVisible = ref(false)
function baseSubmit(value?: string) {
  warn.value = ''
  if (props.dataLength >= 5) {
    ElMessage({
      message: '最多生成5次',
      type: 'warning',
    })
    return
  }
  $emits('submit', value)
}
function justSubmit() {
  baseSubmit()
  visiblePopover.value = false
}

const box = ref()

function handleSubmit() {
  if (feedback.value.trim().length === 0) {
    warn.value = '内容为空，您可点击左边的按钮选择跳过'
    return
  }

  baseSubmit(feedback.value)
  visiblePopover.value = false

  messageVisible.value = true
  setTimeout(() => {
    messageVisible.value = false
  }, 3000)
}

const popover = ref()
onClickOutside(popover, () => {
  visiblePopover.value = false
})
watch(visiblePopover, (val) => {
  if (!val)
    feedback.value = ''
})

watch(feedback, (value) => {
  if (value.trim().length > 0)
    warn.value = ''
})
</script>

<template>
  <div>
    <el-popover
      :visible="visiblePopover"
      width="316"
    >
      <template #reference>
        <div id="gen-argument-refresh-box" ref="box" class="box" @click="handleRefresh">
          <img class="w-[14px] h-[14px]" src="~/assets/images/generate/refresh.png">
          <span class="text2 ml-[6px]">
            <slot />
          </span>
          <div v-if="messageVisible" class="absolute bottom-[-4px] left-0 translate-y-full z-100">
            <div v-if="messageVisible" class="alert-box flex items-center mb-[9px]">
              <div class="i-ll-success text-[#0FA051] mr-[6px]" />
              <span class="text1">
                感谢你的反馈
              </span>
            </div>
          </div>
        </div>
      </template>
      <template #default>
        <div ref="popover" class="w-full">
          <el-input v-model="feedback" :rows="4" placeholder="反馈你想要重新生成的内容" type="textarea" />
          <div class="text-[12px] pt-[5px] text-[#EC1D13]">
            {{ warn }}
          </div>
          <div class="flex items-center justify-between mt-[10px]">
            <el-button size="small" @click="justSubmit">
              不填写，直接生成
            </el-button>
            <el-button type="primary" size="small" @click="handleSubmit">
              我填好了
            </el-button>
          </div>
        </div>
      </template>
    </el-popover>
  </div>
</template>

<style lang="scss" scoped>
.box {
    border-radius: 3px;
    display: inline-block;
    padding: 7px 11px;
    cursor: pointer;
    position: relative;
    background: #FFF;
    border: 1px solid var(--N1, #19222E);
}

.text1 {
    color: var(--N3, #8B9096);
    font-family: Microsoft YaHei UI;
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px; /* 157.143% */
}

.text2 {
    color: var(--N1, #19222E);
    font-size: 14px;
    font-style: normal;
    font-weight: 600;
    line-height: 22px;
}

.alert-box {
    padding: 13px 22px;
    border-radius: 3px;
    background: #FFF;
    box-shadow: 0px 0px 16px 0px rgba(0, 0, 0, 0.12);
    width: 316px;
    height: 46px;
}
</style>
