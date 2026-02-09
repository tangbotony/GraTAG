<script setup lang="ts">
const props = defineProps<{
  index: number
  argumentPlaceholder?: string
  evidencePlaceholder?: string
  value: {
    argument: string
    evidence: string
    key: number
  }
}>()

const $emits = defineEmits<{
  (e: 'delete', value: number): void
}>()

const { value } = toRefs(props)
const isExpand = ref(true)
const visibleDelete = ref(false)

const deleteContainer = ref()
onClickOutside(deleteContainer, () => {
  visibleDelete.value = false
})

function deleteItem() {
  $emits('delete', value.value.key)
  visibleDelete.value = false
}

const isArgumentError = ref(false)

watch(value.value, (val) => {
  if (val.evidence.trim().length > 0 && val.argument.trim().length === 0)
    isArgumentError.value = true

  else
    isArgumentError.value = false
})

const isEvidenceFocus = ref(false)

const isEvidenceInput = ref(false)
function handleEvidenceInput() {
  isEvidenceInput.value = true
}
function handleEvidenceBlur() {
  isEvidenceInput.value = false
  isEvidenceFocus.value = false
}
function handleEvidenceFocus() {
  isEvidenceFocus.value = true
}

const evidencePlaceholder_ = computed(() => {
  if (!props.evidencePlaceholder)
    return ''

  if (props.evidencePlaceholder.length > 20)
    return `${props.evidencePlaceholder?.slice(0, 20)}...`

  else
    return props.evidencePlaceholder
})

const isArgumentFocus = ref(false)
const isArgumentInput = ref(false)
const isArgumentHover = ref(false)
function handleArgumentInput() {
  isArgumentInput.value = true
}
function handleArgumentBlur() {
  isArgumentInput.value = false
  isArgumentFocus.value = false
}
function handleArgumentFocus() {
  isArgumentFocus.value = true
}

const argumentPlaceholder_ = computed(() => {
  if (!props.argumentPlaceholder)
    return ''

  if (props.argumentPlaceholder.length > 20)
    return `${props.argumentPlaceholder?.slice(0, 20)}...`

  else
    return props.argumentPlaceholder
})

function handleArgumentEnter() {
  isArgumentHover.value = true
}
function handleArgumentLeve() {
  isArgumentHover.value = false
}
</script>

<template>
  <div class="flex items-start pl-[10.5px] relative">
    <div class="flex items-center">
      <div
        class="i-ll-triangle text-[8px] cursor-pointer" :class="{
          '-rotate-180': isExpand,
        }"
        @click="isExpand = !isExpand"
      />
      <span class="text1 ml-[6.6px] mr-[9px]">论点{{ props.index + 1 }}</span>
    </div>
    <div
      class="gen-input-container relative"
      :class="{
        'is-error': isArgumentError,
        'is-hover': isArgumentHover,
      }"
      @mouseenter="handleArgumentEnter"
      @mouseleave="handleArgumentLeve"
    >
      <div
        class="relative my-textarea w-[359px]"
      >
        <div v-if="!isArgumentFocus && value.argument.length === 0" class="absolute top-0 left-0 text4 bottom-0 right-0 text-hidden-3 w-full px-[11px] pt-[5px] z-10 pointer-events-none">
          <!-- {{ argumentPlaceholder_ }} -->
          请输入您想参考的论点
        </div>
        <el-input v-model="value.argument" size="small" style="width: 359px" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }" maxlength="100" @focus="handleArgumentFocus" @input="handleArgumentInput" @blur="handleArgumentBlur" />
        <div class="absolute bottom-0 right-[11px] text1">
          <template v-if="isArgumentInput">
            <span
              :class="{
                'text-[#4044ED]': value.argument.length < 250,
                'text-[#EC1D13]': value.argument.length === 250,
              }"
            >{{ value.argument.length }}</span>
            <span>/100</span>
          </template>
          <template v-if="isArgumentHover && !isArgumentInput">
            <div class="i-ll-edit-delete text-[16px] text-[#474E58] mb-[5px]" @click="visibleDelete = true" />
          </template>
        </div>
      </div>
      <div v-if="isArgumentError" class="text-[12px] text-[#EC1D13]">
        不可以只输入论据，但不输入论点哦～
      </div>
      <template v-if="visibleDelete">
        <div ref="deleteContainer" class="delete-container">
          <span class="text1">确认删除这组论点/论据吗？</span>
          <span class="text2" @click="deleteItem">删除</span>
        </div>
      </template>
    </div>
  </div>
  <template v-if="isExpand">
    <div class="pl-[44px] mt-[12px] flex items-start relative">
      <span class="text1 mr-[9px]">论据{{ index + 1 }}</span>
      <div class="relative my-textarea">
        <div v-if="!isEvidenceFocus && value.evidence.length === 0" class="absolute top-0 right-0 text4 h-[59px] text-hidden-3 w-[341px] px-[11px] pt-[5px] z-10 pointer-events-none">
          <!-- {{ evidencePlaceholder_ }} -->
          请输入您想参考的论据
        </div>
        <el-input v-model="value.evidence" size="small" style="width: 341px" type="textarea" :rows="3" maxlength="250" @focus="handleEvidenceFocus" @input="handleEvidenceInput" @blur="handleEvidenceBlur" />
      </div>

      <div v-if="isEvidenceInput" class="absolute bottom-[5px] right-[32px] text1">
        <span
          :class="{
            'text-[#4044ED]': value.evidence.length < 250,
            'text-[#EC1D13]': value.evidence.length === 250,
          }"
        >{{ value.evidence.length }}</span>
        <span>/250</span>
      </div>
    </div>
  </template>
</template>

  <style lang="scss" scoped>
    .text1 {
    color: var(--N1, #19222E);
    font-size: 12px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px; /* 157.143% */
    }

    .text2 {
    color: #EC1D13;
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px; /* 157.143% */
    cursor: pointer;
    }

    .gen-input-container {
    display: inline-block;
    cursor: pointer;
    }

    .delete-container {
    background: #FFFFFF;
    box-shadow: 0px 0px 6px rgba(25, 34, 46, 0.12);
    width: 245px;
    height: 34px;
    position: absolute;
    top: -35px;
    right: px;
    display: flex;
    padding: 6px 9px;
    justify-content: space-between;
    }

    .text3 {
    color: rgb(191, 191, 191);
    font-size: 12px;
    font-weight: 400;
    line-height: 22px;
    }

    .text4 {
    color: rgb(216, 216, 216);
    font-size: 12px;
    font-weight: 350;
    line-height: 18px;
    }

    .text5 {
    color: var(--N1, #19222E);
    font-size: 12px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px; /* 157.143% */
    }

    .my-textarea:deep(textarea) {
    box-shadow: none !important;
    padding-bottom: 0px !important;
    resize: none;
    }

    .my-textarea:deep(.el-textarea) {
    border: 1px solid var(--N6, #D2D4D6);
    padding-bottom: 22px;
    }
  </style>
