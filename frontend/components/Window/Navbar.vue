<script lang="ts" setup>
import { driver } from 'driver.js'

const props = defineProps<{
  positionStyles: { top: number; right: number }
  currentQuoteIndex: number
  amount: number
  title: string
  href: string
}>()

const emits = defineEmits<{
  (e: 'updatePositionStyles', value: { top: number; right: number }): void
  (e: 'close'): void
  (e: 'handleQuoteIndex', value: number): void
}>()

const { positionStyles, currentQuoteIndex, amount, title, href } = toRefs(props)
const btnMove = ref()
function handleQuoteIndexChange(value?: number) {
  if (value === undefined || !amount.value)
    return

  const change = value - currentQuoteIndex.value
  value = currentQuoteIndex.value - change

  if (value < 1 || value > amount.value)
    return

  emits('handleQuoteIndex', value)
}

// drag
const { pressed } = useMousePressed({ target: btnMove })
const { height, width } = useWindowSize()
let mousePosition: null | { dx: number; dy: number } = null
useEventListener(document, 'mousemove', (evt) => {
  if (!pressed.value) {
    mousePosition = null
    return
  }

  evt.preventDefault()

  const lastMousePosition = mousePosition
  mousePosition = {
    dx: evt.clientX,
    dy: evt.clientY,
  }

  let offset = null
  if (lastMousePosition === null) {
    offset = {
      dx: 0,
      dy: 0,
    }
  }
  else {
    offset = {
      dx: mousePosition!.dx - lastMousePosition.dx,
      dy: mousePosition!.dy - lastMousePosition.dy,
    }
  }

  if (positionStyles.value) {
    let top_ = positionStyles.value.top + offset.dy
    if (top_ < 0)
      top_ = 0
    else if (top_ > (height.value - 48))
      top_ = height.value - 48

    let right_ = positionStyles.value.right - offset.dx

    if (right_ < -408)
      right_ = -408
    else if (right_ > (width.value - 444))
      right_ = width.value - 444

    emits('updatePositionStyles', {
      top: top_,
      right: right_,
    })
  }
})

const numberInput = ref<HTMLElement | null>()
const maxWidth = computed(() => {
  if (!numberInput.value)
    return 180

  const { width } = numberInput.value.getBoundingClientRect()
  return 460 - width - 48 - 16 - 20
})

onMounted(() => {
  if (currentUser.value?.extend_data.quote_window_step_1)
    return
  const driverObj = driver({
    doneBtnText: '我知道了',
    showProgress: false,
    showButtons: ['next'],
    steps: [
      {
        element: '#quote-window-drag_btn',
        popover: {
          description: `<div class="flex items-center text-white">
            <span>点击上方</span>
            <div style="border: 1px solid white;border-radius: 3px; margin: 0px 4px;" >
              <div class="i-ll-drag text-[20px] text-white"></div>
            </div>
            <span>可以拖拽文件浮层</span>
          </div>`,
        },
      },
    ],
  })
  driverObj.drive()
  updateUserInfo('quote_window_step_1', true)
})
function spanLinkClick(hrefdata: string) {
  if (!hrefdata.includes('http') && hrefdata.includes('sourceid')) {
    const sourceidstr = getHrefParam('sourceid', hrefdata)
    const fileext = getHrefParam('ext', hrefdata)
    const version = getHrefParam('version', hrefdata)
    if (fileext !== 'txt') {
      let url = `/filePreview?pdfid=${sourceidstr}&fileext=${fileext}`
      if (version)
        url += '&version=v2'

      window.open(url, '_blank')
    }
  }
}
function getHrefParam(txt: string, params: string) {
  const paramsArray = params.split('&')
  let str = ''
  paramsArray.forEach((item: string) => {
    const [key, value] = item.split(':')
    if (key === txt)
      str = value
  })
  return str
}
</script>

<template>
  <div class="w-full h-[48px] flex items-center justify-between px-[16px] bg-[#fff]">
    <div class="flex items-center">
      <div id="quote-window-drag_btn" ref="btnMove" class="btn-move flex items-center justify-center">
        <div class="i-ll-drag text-[20px] text-[#666666]" />
      </div>
      <el-tooltip placement="bottom" effect="light" :disabled="pressed">
        <template #content>
          <div class="window-subtitle max-w-[265px]" @click.stop>
            {{ title }}
          </div>
        </template>
        <template #default>
          <div class="px-[12px] truncate window-title cursor-pointer" :style="{ maxWidth: `${maxWidth}px` }">
            <span v-if="href && href.indexOf('http') === -1 && href.indexOf('sourceid') > -1" class="link" :hrefdata="href" @click="spanLinkClick(href || '')">{{ title }}</span>
            <NuxtLink v-else class="link" :href="href" target="__blank">
              {{ title }}
            </NuxtLink>
          </div>
        </template>
      </el-tooltip>
    </div>
    <div class="flex items-center w-max justify-end">
      <div ref="numberInput" class="pr-[12px] w-max quote-input-number">
        <span class="window-info mr-[8px]">被引用情况:</span>
        <el-input-number
          :model-value="currentQuoteIndex"
          size="small"
          controls-position="right"
          @change="handleQuoteIndexChange"
        />
        <span class="window-info ml-[8px]">/ {{ amount }}</span>
      </div>
      <div class="i-ll-close text-[16px] cursor-pointer" @click="emits('close')" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.window {
  &-title {
    font-size: 16px;
    font-weight: normal;
    line-height: 24px;
    letter-spacing: 0em;
    color: rgba(0, 0, 0, 0.9);
  }
  &-subtitle {
    font-size: 14px;
    font-weight: normal;
    line-height: 22px;
    letter-spacing: 0em;
    color: rgba(0, 0, 0, 0.88);
  }
  &-info {
    font-size: 12px;
    font-weight: normal;
    line-height: normal;
    letter-spacing: 0em;
    color: rgba(0, 0, 0, 0.6);
  }
}

.quote-input-number:deep( .el-input__wrapper) {
 padding: 1px 31px 1px 4px;
}

.quote-input-number:deep(.el-input-number--small) {
  width: 52px !important;
}

.btn-move {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  &:hover {
    background: #F3F3F3;
  }
  cursor: pointer;
}

.link:hover {
  text-decoration: none;
}
</style>
