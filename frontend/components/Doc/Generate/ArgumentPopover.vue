<script setup lang="ts">
const props = defineProps<{
  text: string
  originText?: string
  isUp: boolean
  isDown: boolean
  maxlength: number
  width?: string
  placement: any
}>()

const $emit = defineEmits<{
  (e: 'update:text', value: string): void
  (e: 'update:originText', value: string): void
  (e: 'update:isUp', value: boolean): void
  (e: 'update:isDown', value: boolean): void
  (e: 'show'): void
  (e: 'hide'): void
}>()

const box = ref()
const visible = ref(false)
const inputValue = ref('')
const slotContainer = ref()

const popover = ref()
const currentPopverInstance = inject<Ref<any>>('popverInstance')!
const position = ref({ top: 0, left: 0 })

const currentInstance = getCurrentInstance()!

onClickOutside(box, (val) => {
  if (inputValue.value.trim() && visible.value) {
    let text = inputValue.value.trim()
    text = text.replaceAll('\n', '')
    $emit('update:text', text)
  }

  visible.value = false
})

const visiblePopover = ref(false)
const editInput = ref()
async function edit() {
  visible.value = true
  inputValue.value = props.text
  visiblePopover.value = false
  await nextTick()
  editInput.value?.focus()
}
const clearTimerId = ref<any>(0)

function handlePopoverEnter() {
  clearTimeout(clearTimerId.value)
}

function handlePopoverLeave() {
  visiblePopover.value = false
}

watch(visible, (value) => {
  if (value)
    $emit('show')
  else
    $emit('hide')
})

function handleShow(event: MouseEvent) {
  currentPopverInstance.value?.exposed.hide()
  currentPopverInstance.value = currentInstance
  position.value.left = event.clientX
  position.value.top = event.clientY - 58

  visiblePopover.value = true

  clearTimerId.value = setTimeout(() => {
    visiblePopover.value = false
  }, 1000 * 3)
}

defineExpose({
  hide: () => {
    visiblePopover.value = false
  },
})
</script>

<template>
  <el-popover
    ref="popover"
    :placement="placement"
    :visible="visiblePopover"
    :hide-after="0"
    :width="props.width || 'auto'"
    :popper-style="{
      minWidth: '10px !important',
      left: `${position.left}px !important`,
      top: `${position.top}px !important`,
      bottom: 'auto !important',
      transform: 'translateX(-50%)',
      padding: 0,
    }"
  >
    <template #reference>
      <div
        ref="slotContainer"
        class="item w-full"
        @click="handleShow"
      >
        <slot name="reference" />
      </div>
    </template>
    <template #default>
      <div
        class="flex items-center justify-start px-[16px] py-[8px]"
        @mouseenter="handlePopoverEnter"
        @mouseleave="handlePopoverLeave"
      >
        <div class="i-ll-edit text-black cursor-pointer" @click="edit" />
        <div
          class="cursor-pointer ml-[16px]"
          :class="{
            'i-ll-up-line': !props.isUp,
            'i-ll-up-fill': props.isUp,
            'text-[#8B9096]': !props.isUp,
            'text-[#4044ED]': props.isUp,
          }"
          @click="$emit('update:isUp', !props.isUp)"
        />
        <div
          class="rotate-180 cursor-pointer ml-[16px]"
          :class="{
            'i-ll-up-line': !props.isDown,
            'i-ll-up-fill': props.isDown,
            'text-[#8B9096]': !props.isDown,
            'text-[#4044ED]': props.isDown,
          }"
          @click="$emit('update:isDown', !props.isDown)"
        />
        <slot name="default" />
      </div>
    </template>
  </el-popover>

  <div
    v-if="visible"
    ref="box" class="box z-100"
    :style="{
      top: `${slotContainer.offsetTop - 12}px`,
    }"
  >
    <el-input
      ref="editInput"
      v-model="inputValue"
      size="small"
      type="textarea"
      :autosize="{ minRows: 9, maxRows: 12 }"
      style="width: 406px;"
      :maxlength="props.maxlength"
    />
    <div class="flex items-center justify-end text1">
      <span
        :class="{
          'text-[#4044ED]': inputValue.length < props.maxlength,
          'text-[#F56C6C]': inputValue.length === props.maxlength,
        }"
      >{{ inputValue.length }}</span>
      <span class="text-black">/{{ props.maxlength }}</span>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.text1 {
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px; /* 157.143% */
}

.box {
    border-radius: 3px;
    background: #FFF;
    box-shadow: 0px 0px 10px 0px rgba(25, 34, 46, 0.16);
    padding: 12px 7px 8px 12px;
    position: absolute;
    top: -12px;
    left: 50%;
    transform: translateX(-50%);
    bottom: 0;
    right: 0;
    width: 428px;
    height: 225px;

    &:deep(textarea) {
      font-size: 13px !important;
    }
}
</style>
