<script setup lang="ts">
const props = defineProps<{
  visibleRightSideBar: boolean
  positionStyles: null | { top: number; right: number }
  currentIndex: number
  amount: number
  title: string
  href: string
}>()

const $emits = defineEmits<{
  (e: 'handleIndex', value: number): void
  (e: 'clear'): void
  (e: 'update:positionStyles', value: { top: number; right: number }): void
}>()

const { positionStyles, amount, title, href, currentIndex } = toRefs(props)
const cardRef = ref<HTMLElement | null>(null)

function clear() {
  $emits('clear')
}

const { height } = useWindowSize()
const maxHeight = 720
const cardHeight = computed(() => {
  if (height.value < (106 + 8 + maxHeight))
    return height.value - 106 - 8

  return maxHeight
})

function updatePositionStyles(value: { top: number; right: number }) {
  $emits('update:positionStyles', value)
}

function handleQuoteIndex(index: number) {
  $emits('handleIndex', index)
}

watch(() => props.visibleRightSideBar, (value) => {
  if (value) {
    if (positionStyles.value && positionStyles.value.right < 494)
      $emits('update:positionStyles', { ...positionStyles.value, right: 494 })
  }
  else {
    if (positionStyles.value)
      $emits('update:positionStyles', { ...positionStyles.value, right: 24 })
  }
})

const windowWidth = ref(460)
const leftDragLine = ref(null)
const rightDragLine = ref(null)
let mousePositionX: null | number = null
let currentDirection = ''
const isDragging = ref(false)

function dragStart(direc: string) {
  isDragging.value = true
  currentDirection = direc
  window.addEventListener('mousemove', dragging, { passive: true })
  window.addEventListener('mouseup', dragStop, {
    passive: true,
    once: true,
  })
}

function dragging(evt: MouseEvent) {
  const lastMousePositionX = mousePositionX
  mousePositionX = evt.clientX

  let offsetX = null
  if (lastMousePositionX === null)
    offsetX = 0
  else
    offsetX = mousePositionX - lastMousePositionX

  if (currentDirection === 'left') {
    windowWidth.value -= offsetX
  }
  else if (currentDirection === 'right') {
    windowWidth.value += offsetX
    if (positionStyles.value)
      $emits('update:positionStyles', { ...positionStyles.value, right: positionStyles.value.right - offsetX })
  }
}

function dragStop() {
  window.removeEventListener('mousemove', dragging)
  currentDirection = ''
  mousePositionX = null
  isDragging.value = false
}
</script>

<template>
  <div
    v-if="positionStyles"
    ref="cardRef"
    :style="{
      ...{ top: `${positionStyles.top}px`, right: `${positionStyles.right}px` },
      height: `${cardHeight}px`,
      width: `${windowWidth}px`,
      minWidth: `${windowWidth}px`,
      maxWidth: `${windowWidth}px`,
    }"
    class="container"
  >
    <WindowNavbar
      :position-styles="positionStyles"
      :current-quote-index="currentIndex"
      :amount="amount"
      :title="title"
      :href="href"
      @update-position-styles="updatePositionStyles"
      @handle-quote-index="handleQuoteIndex"
      @close="clear"
    />
    <slot />
    <div v-if="isDragging" class="absolute top-[48px] left-[3px] right-[3px] bottom-0 absolute" />
    <div ref="leftDragLine" class="w-[5px] top-0 bottom-0 absolute left-0 drag-v-line" @mousedown.prevent="dragStart('left')" />
    <div ref="rightDragLine" class="w-[5px] top-0 bottom-0 absolute right-0 drag-v-line" @mousedown.prevent="dragStart('right')" />
  </div>
</template>

<style lang="scss" scoped>
.container {
    border-radius: 12px;
    overflow: hidden;
    background: #F3F3F3;
    border: 1px solid #DCDCDC;
    box-shadow: 0px 6px 16px 0px rgba(0, 0, 0, 0.08),0px 3px 6px -4px rgba(0, 0, 0, 0.12),0px 9px 28px 8px rgba(0, 0, 0, 0.05);
    position: absolute;
    display: flex;
    flex-direction: column;
    z-index: 100;
    pointer-events: auto;
}

.text-content {
  font-size: 16px;
  font-weight: 400;
  line-height: 26px;
  color: rgba(0, 0, 0, 0.6);
  background: #FFFFFF;
  white-space: pre-wrap;
}

.drag-v-line {
  cursor: col-resize;
}
</style>
