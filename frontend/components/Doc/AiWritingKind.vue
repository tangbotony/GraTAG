<script setup lang="ts">
import { NEWS_KIND } from '~/consts/editor'

const props = defineProps<{
  initType: string
}>()

const $emits = defineEmits<{
  (e: 'closed'): void
  (e: 'hide'): void
  (e: 'show'): void
  (e: 'nextTxt', value: string): void
}>()
const radioType = ref(props.initType || 'review')
function close() {
  $emits('closed')
}
function next() {
  $emits('nextTxt', radioType.value)
}
function radioDivClick(val: string) {
  radioType.value = val
}
const kinds = [
  {
    type: NEWS_KIND.Review,
    title: '评论文章',
    subtitle: '通过填写提纲要领，AI自动生成完整评论文章',
  },
  {
    type: NEWS_KIND.Summarize,
    title: '综述文章',
    subtitle: '通过上传文件，AI自动生成完整综述文章',
  },
  {
    type: NEWS_KIND.Message,
    title: '消息稿件',
    subtitle: '通过上传文件，AI自动生成完整消息稿件',
  },
  {
    type: NEWS_KIND.Communication,
    title: '通讯稿件',
    subtitle: '通过上传文件，AI自动生成完整通讯稿件',
  },
  {
    type: NEWS_KIND.ExclusiveInterview,
    title: '专访稿件',
    subtitle: '通过上传文件，AI自动生成完整专访稿件',
  },
  {
    type: NEWS_KIND.Feature,
    title: '特写稿件',
    subtitle: '通过上传文件，AI自动生成完整特写稿件',
  },
  {
    type: NEWS_KIND.Others,
    title: '其他稿件',
    subtitle: '通过上传文件，AI自动生成完整文章',
  },
]
</script>

<template>
  <div class="flex-1 overflow-y-auto w-full relative">
    <div class="sticky top-0 w-full flex items-center justify-between py-[21px] px-[16px] mb-[5px] bg-white z-10">
      <div class="flex items-center">
        <div class="i-custom:ai-ring w-[20px] h-[20px]" />
        <span class="text1">AI全文写作</span>
      </div>
      <div class="i-ll-close text-[20px] text-[#D9D9D9] mx-[8px] cursor-pointer" @click="close" />
    </div>
    <div class="box">
      <div
        v-for="item in kinds"
        :key="item.type"
        class="radioDiv"
        :class="{ selectDiv: radioType === item.type }"
        @click="radioDivClick(item.type)"
      >
        <div class="tit">
          {{ item.title }}
        </div>
        <div class="subhead">
          {{ item.subtitle }}
        </div>
        <el-radio v-model="radioType" class="radio" :value="item.type" size="large" />
      </div>
    </div>
  </div>
  <div class="h-[69px] border-t-1 w-full border-[rgba(217, 217, 217, 1)] flex items-center justify-end px-[24px]">
    <div class="btn-bottom-container flex">
      <div
        class="px-[11px] py-[7px] text1 flex items-center justify-center btn-bottom cursor-pointer"
        @click="next"
      >
        <span class="text-[#4044ED]">
          <template v-if="radioType === 'review'">
            下一步：填写提纲要领
          </template>
          <template v-else-if="radioType !== 'review'">
            下一步：上传文件
          </template>
        </span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.box {
  margin: 16px;
  .radioDiv {
    border: 1px solid #DCDCDC;
    height: 85px;
    border-radius: 16px;
    padding: 20px;
    padding-left: 60px;
    margin-bottom: 16px;
    cursor: pointer;
    position: relative;
    .tit {
      font-size: 16px;
      color: rgba(0, 0, 0, 0.87);
      height: 22px;
      line-height: normal;
      margin-bottom: 8px;
    }
    .subhead {
      font-family: Alibaba PuHuiTi 2.0;
      font-size: 12px;
      font-weight: normal;
      line-height: normal;
      letter-spacing: 0em;
      color: rgba(0, 0, 0, 0.65);
    }
  }
  .radioDiv:hover{
    border: 1px solid #4044ED;
  }
  .radioType1 {
    position: absolute;
    top: 44px;
    left: 20px;
  }
  .radioType2 {
    position: absolute;
    top: 144px;
    left: 20px;
  }
  .selectDiv {
    border: 1px solid #4044ED;
  }
}
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

.radio {
  position: absolute;
  left: 24px;
  top: 50%;
  transform: translateY(-50%);
}
</style>
