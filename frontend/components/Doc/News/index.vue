<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'
import Draggable from 'vuedraggable'
import { WarningFilled } from '@element-plus/icons-vue'
import type { UploadUserFile } from 'element-plus'
import type { RuleForm } from './Step1.vue'
import { NEWS_KIND, NEWS_KIND_MAP } from '~/consts/editor'

const props = defineProps<{
  editor: Editor
  scrollContainer: any
  sessionId: string
  type: string
}>()
const $emits = defineEmits<{
  (e: 'closed'): void
  (e: 'hide'): void
  (e: 'show'): void
  (e: 'back'): void
}>()

const step = ref(1)
const step1Form = ref()

const loadingVisible = ref(false)
const datalist = ref<pointDataType[]>([])
const dataTotallist = ref<pointDataType[][]>([])
const textareaShow = ref(-1)
const DraggableFlag = ref(true)
const pointsTitle = ref('')
const pageIndex = ref(1)
const showPointMenu = ref(-1)
const pointShowFlag = ref(false)
const materialData = ref<string[]>([])
const addPointNum = ref(0)
const feedbackVisible = ref(false)
const feedbackTxt = ref('')
const GenerateFullTextFlag = ref(false)
const visibleStep4 = ref(false)
const step4Data = ref<any>()
const pointEditInput = ref()
const pointAddInput = ref()
const controller = ref<undefined | AbortController>()

// step1
const ruleForm = reactive<RuleForm>({
  theme: '',
  fileData: [],
  reference: ['files'],
  num: undefined,
  style: 'strict',
  direction: '',
})
const fileList = ref<UploadUserFile[]>([])
provide('step1_fileList', fileList)
const isStepChange = ref(false)
watch(step, (val) => {
  if (val === 2)
    isStepChange.value = false
})
watch([ruleForm, fileList], () => {
  isStepChange.value = true
})

function close() {
  visibleStep4.value = false
  step4Data.value = null
  props.editor.setEditable(true)
  $emits('closed')
}
function handleEnterPoint(index: number) {
  if (textareaShow.value === -1) {
    showPointMenu.value = index
  }
  else {
    ElMessage({
      message: '有内容正在编辑中，请先提交或取消',
      type: 'warning',
    })
  }
}

function handlePrevStep() {
  dataTotallist.value = []
  if (step.value === 2)
    step.value = 1
  else if (step.value === 1)
    $emits('back')
}
interface pointDataType {
  title: string
  title_ori: string
}
function submit() {
  if (step.value === 1) {
    const isLoading = fileList.value.some((item) => {
      return item.status === 'uploading'
    })
    if (isLoading) {
      ElMessage({
        message: '文件正在上传中，请稍后',
        type: 'warning',
      })
      return
    }
    const allWorCount = fileList.value.reduce((prev, cur: any) => {
      return prev + cur.response.message
    }, 0)
    if (allWorCount < 800) {
      ElMessage({
        message: '文件总字数要大于800字',
        type: 'warning',
      })
      return
    }
    step1Form.value?.formRef?.validate(async (valid: boolean) => {
      if (valid) {
        if (!isStepChange.value) {
          step.value = 2
          return
        }

        materialData.value = ruleForm.fileData.map(item => (item.response as { mid: string })!.mid)
        const obj: any = {
          material_id: materialData.value,
          sub_title_his: [],
          session_id: props.sessionId,
          kind: props.type,
          style: ruleForm.style,
        }

        if (ruleForm.theme)
          obj.topic = ruleForm.theme

        if (ruleForm.direction)
          obj.direction = ruleForm.direction

        loadingVisible.value = true
        controller.value?.abort()
        controller.value = new AbortController()
        generateSubTitle(obj, controller.value).then((res) => {
          loadingVisible.value = false
          if (res.data.value?.result && res.data.value.result.length === 0) {
            ElMessage({
              message: '算法返回为空',
              type: 'warning',
            })
          }
          if (res.data.value?.result && res.data.value.result.length > 0) {
            const pointData: pointDataType[] = []
            res.data.value.result.forEach((item: any) => {
              if (typeof (item) === 'object' && 'title' in item) {
                const obj = {
                  title: item.title,
                  title_ori: item.title,
                }
                pointData.push(obj)
              }
            })
            dataTotallist.value.push(pointData)

            datalist.value = dataTotallist.value[0]
            step.value = 2
          }
        })
      }
    })
  }
  else {
    $emits('hide')
    const resultData: pointDataType[] = []
    dataTotallist.value.forEach((node) => {
      node.forEach((item: pointDataType) => {
        resultData.push(item)
      })
    })
    const subTitleData = dataTotallist.value[pageIndex.value - 1]
    step4Data.value = unref({
      material_id: materialData.value,
      sub_title: subTitleData,
      result_his: resultData,
      review_length: ruleForm.num ? ruleForm.num : undefined,
      use_trusted_website: ruleForm.reference.length > 1,
      session_id: props.sessionId,
      kind: props.type,
      style: ruleForm.style,

    })
    if (ruleForm.theme)
      step4Data.value.topic = ruleForm.theme

    if (ruleForm.direction)
      step4Data.value.direction = ruleForm.direction

    visibleStep4.value = true
    props.editor.setEditable(false)
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
function cancelReq() {
  controller.value?.abort()
  ElMessage({
    message: '已取消生成',
    type: 'error',
  })
  loadingVisible.value = false
}

function handleConfirmPop(index: number) {
  datalist.value.splice(index, 1)
  showPointMenu.value = -1
}
function handleCancelPop() {
  showPointMenu.value = -1
}
function purifyEdit(index: number) {
  if (pointShowFlag.value) {
    ElMessage({
      message: '有内容正在编辑中，请先提交或取消',
      type: 'error',
    })
    return
  }

  showPointMenu.value = -1
  DraggableFlag.value = false
  textareaShow.value = index
  nextTick(() => {
    pointEditInput.value?.focus()
  })
}
function textareaBlur(element: any) {
  if (element.title.trim().length === 0)
    return

  textareaShow.value = -1
  DraggableFlag.value = true
}
function pagePrv() {
  if ((pageIndex.value !== 1) && !pointShowFlag.value) {
    pageIndex.value = pageIndex.value - 1
    datalist.value = dataTotallist.value[pageIndex.value - 1]
  }
}
function pageNext() {
  if ((pageIndex.value !== dataTotallist.value.length) && !pointShowFlag.value) {
    pageIndex.value = pageIndex.value + 1
    datalist.value = dataTotallist.value[pageIndex.value - 1]
  }
}
function addPoint() {
  pointShowFlag.value = true
  pointsTitle.value = ''
  DraggableFlag.value = false
  nextTick(() => {
    pointAddInput.value?.focus()
  })
}
function changeSetPoint() {
  feedbackTxt.value = ''
  if (dataTotallist.value.length > 1)
    feedbackVisible.value = true
  else
    getDataChangeSet()
}
function directClick() {
  feedbackVisible.value = false
  getDataChangeSet()
}
function filledClick() {
  feedbackVisible.value = false
  getDataChangeSet()
}
interface pointDataitem {
  title: string
}
function getDataChangeSet() {
  const subTitleHisData: pointDataType[] = []
  dataTotallist.value.forEach((node: pointDataType[]) => {
    node.forEach((item) => {
      subTitleHisData.push(item)
    })
  })
  const obj: any = {
    material_id: materialData.value,
    sub_title_his: [],
    session_id: props.sessionId,
    kind: props.type,
    style: ruleForm.style,
  }

  if (ruleForm.theme)
    obj.topic = ruleForm.theme

  if (ruleForm.direction)
    obj.direction = ruleForm.direction
  loadingVisible.value = true
  controller.value?.abort()
  controller.value = new AbortController()
  generateSubTitle(obj, controller.value).then((res) => {
    loadingVisible.value = false
    if (res.data.value?.result && res.data.value.result.length === 0) {
      ElMessage({
        message: '算法返回为空',
        type: 'warning',
      })
    }
    if (res.data.value?.result && res.data.value.result.length > 0) {
      const pointData: pointDataType[] = []
      res.data.value.result.forEach((item: pointDataitem) => {
        const obj = {
          title: item.title,
          title_ori: item.title,
        }
        pointData.push(obj)
      })
      dataTotallist.value.push(pointData)
      datalist.value = dataTotallist.value[dataTotallist.value.length - 1]
      pageIndex.value = dataTotallist.value.length
    }
  })
}
function confirmPoint() {
  if (pointsTitle.value.trim().length === 0)
    return

  DraggableFlag.value = true
  pointShowFlag.value = false
  const obj = {
    title: pointsTitle.value,
    title_ori: pointsTitle.value,
  }
  datalist.value.push(obj)
  addPointNum.value = addPointNum.value + 1
}
function cancelPoint() {
  DraggableFlag.value = true
  pointShowFlag.value = false
}

const step1NextBtnText = computed(() => {
  if (props.type === 'others')
    return '内容提炼'
  return `${NEWS_KIND_MAP[props.type]}内容提炼`
})

const step2NextBtnText = computed(() => {
  if (props.type === 'others')
    return '生成全文'
  return `生成${NEWS_KIND_MAP[props.type]}全文`
})

const popover = ref()
onClickOutside(popover, () => {
  feedbackVisible.value = false
})

function handleDataList(value: any) {
  datalist.value = value
  dataTotallist.value[pageIndex.value - 1] = datalist.value
}

const step1Time = computed(() => {
  return 10
})
</script>

<template>
  <div class="flex-1 overflow-y-scroll w-full relative" @click="showPointMenu = -1">
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
          <div>文件上传</div>
        </template>
      </el-step>
      <el-step>
        <template #title>
          <div>内容提炼</div>
        </template>
      </el-step>
    </el-steps>
    <div v-if="loadingVisible" class="w-full h-[250px] flex items-center justify-center">
      <DocLoading :duration="step1Time" @cancle="cancelReq" />
    </div>
    <div v-if="step === 1">
      <DocNewsStep1
        ref="step1Form"
        :loading-visible="loadingVisible"
        :rule-form="ruleForm"
        :type="props.type"
      />
    </div>
    <div v-if="step === 2 " class="ulkeypoints">
      <Draggable v-if="!loadingVisible" :model-value="datalist" item-key="id" animation="300" :sort="DraggableFlag" @update:model-value="handleDataList">
        <template #item="{ element, index }">
          <div class="purifyList" :class="{ liediting: textareaShow === index && showPointMenu === -1 }">
            <div class="dragicon i-ll-sanheng text-[18px]" />
            <span>
              {{ index + 1 }}. {{ element.title }}
            </span>
            <el-input
              v-if="textareaShow === index && showPointMenu === -1"
              ref="pointEditInput"
              v-model="element.title"
              class="textareaEdit"
              maxlength="100"
              placeholder="请输入要点"
              show-word-limit
              type="textarea"
              @blur="textareaBlur(element)"
            />

            <div class="opicon">
              <div class="iconbox" @click.stop="handleEnterPoint(index)">
                ...
              </div>
              <div v-if="showPointMenu === index" class="opshad" />
              <div v-if="showPointMenu === index" class="pointmenubox">
                <div class="menuinner">
                  <div class="menuli" @click.stop="purifyEdit(index)">
                    <div class="i-ll-edit  ml-[0px]" />
                    编辑
                  </div>

                  <el-popconfirm
                    title="确认删除这个要点吗?"
                    width="200"
                    placement="top"
                    confirm-button-text="确认"
                    cancel-button-text="取消"
                    icon-color="#da5d14"
                    :icon="WarningFilled"
                    @confirm="handleConfirmPop(index)"
                    @cancel="handleCancelPop"
                  >
                    <template #reference>
                      <div class="menuli" @click.stop="">
                        <div class="i-ll-edit-delete  ml-[0px]" />
                        删除
                      </div>
                    </template>
                  </el-popconfirm>
                </div>
              </div>
            </div>
          </div>
        </template>
      </Draggable>
      <div v-if="pointShowFlag" class="addBox">
        <el-input
          ref="pointAddInput"
          v-model="pointsTitle"
          class="textareaAdd"
          maxlength="100"
          placeholder="请输入要点"
          type="textarea"
          :autosize="{ minRows: 6, maxRows: 6 }"
        />
        <div class="purifyBtnBox flex items-center">
          <div class="mr-[8px] text-[12px] leading-[22px]">
            <span
              :class="{
                'text-[#4044ED]': pointsTitle.trim().length > 0,
                'text-red': pointsTitle.trim().length === 0,
              }"
            >{{ pointsTitle.length }}</span>
            <span class="text-n1-color">/100</span>
          </div>
          <el-button size="small" @click="cancelPoint">
            取消
          </el-button>
          <el-button type="primary" size="small" @click="confirmPoint">
            确认
          </el-button>
        </div>
      </div>
      <div v-if="!loadingVisible" class="changeBtnBox changeBtnBoxpos">
        <el-button class="xzyd" size="small" plain round @click="addPoint">
          新增要点
        </el-button>
        <el-button v-if="dataTotallist.length < 5" size="small" plain round :class="pointShowFlag ? 'disabledbtn' : ''" @click="changeSetPoint">
          <img style="width: 12px;height: 12px;margin-right: 5px;" src="~/assets/images/generate/refresh.png">
          换一组
        </el-button>
        <div v-if="dataTotallist.length > 1" class="pagesBox">
          <div class="pagesBtn" :class="{ pagesBtnDis: pageIndex === 1 }" @click="pagePrv">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"><path fill="currentColor" d="M609.408 149.376 277.76 489.6a32 32 0 0 0 0 44.672l331.648 340.352a29.12 29.12 0 0 0 41.728 0 30.592 30.592 0 0 0 0-42.752L339.264 511.936l311.872-319.872a30.592 30.592 0 0 0 0-42.688 29.12 29.12 0 0 0-41.728 0z" /></svg>
          </div>
          <div>{{ pageIndex }}/{{ dataTotallist.length }}</div>
          <div class="pagesBtn" :class="{ pagesBtnDis: pageIndex === dataTotallist.length }" @click="pageNext">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"><path fill="currentColor" d="M340.864 149.312a30.592 30.592 0 0 0 0 42.752L652.736 512 340.864 831.872a30.592 30.592 0 0 0 0 42.752 29.12 29.12 0 0 0 41.728 0L714.24 534.336a32 32 0 0 0 0-44.672L382.592 149.376a29.12 29.12 0 0 0-41.728 0z" /></svg>
          </div>
        </div>
        <div v-if="feedbackVisible" class="feedbackBoxwai">
          <div ref="popover" class="feedbackBox">
            <div>
              <el-input
                v-model="feedbackTxt"
                placeholder="反馈你要重新生成的内容"
                type="textarea"
                :autosize="{ minRows: 4, maxRows: 4 }"
              />
            </div>
            <div class="feedbackBtnBox">
              <el-button id="directBtn" @click="directClick">
                不填写, 直接生成
              </el-button>
              <el-button id="filledBtn" class="wthl" @click="filledClick">
                我填好了
              </el-button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="loadingVisible && !GenerateFullTextFlag" class="changeBtnBox">
        <el-button size="small" plain round>
          <img style="width: 12px;height: 12px;margin-right: 5px;" src="~/assets/images/generate/refresh.png">
          重新生成中...
        </el-button>
      </div>
    </div>
  </div>
  <div class="h-[69px] border-t-1 w-full border-[rgba(217, 217, 217, 1)] flex items-center justify-end px-[24px] outline_btn ">
    <div
      class="w-[100px] h-[36px] mr-[12px] text1 flex items-center justify-center cursor-pointer border-1 border-[#DFE1E2] rounded-[100px]"
      :class="loadingVisible ? 'disabledbtn' : ''"
      @click="handlePrevStep"
    >
      <span>
        上一步
      </span>
    </div>
    <div class="btn-bottom-container flex">
      <div
        class="px-[11px] py-[7px] text1 flex items-center justify-center btn-bottom cursor-pointer"
        :class="pointShowFlag ? 'disabledbtn' : ''"
        @click="submit"
      >
        <span class="text-[#4044ED]">
          <div v-if="step === 1">
            下一步：{{ step1NextBtnText }}
          </div>
          <div v-else-if="step === 2">
            下一步：{{ step2NextBtnText }}
          </div>
        </span>
      </div>
    </div>
  </div>

  <DocNewsStep4
    v-if="visibleStep4"
    :editor="props.editor"
    :scroll-container="scrollContainer"
    :data="step4Data"
    :type="props.type"
    @apply="step4Apply"
    @back="step4Back"
  />
</template>

<style lang="scss" scoped>
.disabledbtn{
  pointer-events: none;
  cursor: pointer;
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

.demo-ruleForm {
  &:deep(.el-upload-list__item) {
    width: 100%!important;
    height: auto!important;
  }
  &:deep(.el-input-number .el-input__inner) {
    text-align: left;
    line-height:32px;
  }
}
::v-deep .el-form--default.el-form--label-top .el-form-item .el-form-item__label{
  color:#000;
}
.el-form-item{
  margin-bottom: 20px;
}
::v-deep .el-form-item.is-required:not(.is-no-asterisk).asterisk-left>.el-form-item__label::before{
  content: " ";
}
::v-deep .el-input__inner{
  --el-input-inner-height: 32px;
}
::v-deep .el-form-item.is-required:not(.is-no-asterisk).asterisk-left>.el-form-item__label:after{
  color: var(--el-color-danger);
    content: "*";
    margin-left: 4px;
}
::v-deep .el-form--default.el-form--label-top .el-form-item .el-form-item__label{
  height: 38px;
  padding-right: 0px;
  margin-bottom:0px;
}
.outline_btn{
  display: flex;
  flex-direction: row;
  justify-content: space-between;
}
.btnupload{
  border: 1px solid #4044ED;
  box-sizing: border-box;
  width: 112px;
  height: 32px;
  border-radius: 16px;
  font-size: 14px;
  color: #4044ED;
}
.btnback{
  height: 36px;
  line-height: 36px;
  border-radius: 30px;
  align-items: center;
  padding: 0px 16px;
  gap: 8px;
  background: #FFFFFF;
  border: 1px solid #DCDCDC;
  font-size: 14px;
  color: #4044ED;
  display: flex;
  align-items: center;
}

.ulkeypoints{
  padding: 16px;
  padding-top: 36px;
  font-size: 14px;
  .purifyList {
    cursor: pointer;margin-bottom: 16px; background: #F8F8F8;  border-radius: 8px; position: relative; line-height: 22px; padding: 16px 46px 16px 16px;
    .dragicon{ position:absolute; left:-12px; top:50%; margin-top:-4px; display: none; cursor:grab; }
    .opicon{
       color:#8B8B8B; line-height: 12px; text-align: center;
      cursor: pointer; position: absolute; right: 16px; top: 50%; margin-top: -9px; color: rgba(0, 0, 0, 0.88);
      .iconbox{width: 18px; height: 18px;background: #E7E7E7; border-radius: 4px;}
      .opshad{ position: absolute; right: 18px;; height: 18px; width: 80px; top: 0px;}
      .pointmenubox{
        position: absolute; top: 18px; right:-30px; width: 180px;z-index: 2;   text-align: left;

        .menuinner{
          border-radius: 6px;
          background: #FFFFFF; margin:0 30px;box-shadow: 0px 6px 16px 0px rgba(0, 0, 0, 0.08),0px 3px 6px -4px rgba(0, 0, 0, 0.12),0px 9px 28px 8px rgba(0, 0, 0, 0.05);
          padding: 4px;
          gap: 4px;
          display: flex;
          flex-direction: column;
        }
        .menuli{
           line-height: 40px; cursor: pointer; padding: 0px 12px;border-radius: 4px; display: flex; gap: 6px; align-items: center; color: rgba(0, 0, 0, 0.6);;
           &:hover{background: rgba(0, 0, 0, 0.06); color: rgba(0, 0, 0, 0.88);}
        }
      }
    }

    .textareaEdit {
      position: absolute;
      top: 0;
      left: 0;
      z-index: 10;
      height: 100%;
      &:deep(.el-textarea__inner) {
        min-height: 100%!important;
      }
    }
    &:hover{
      .dragicon{ display: block;}
    }
  }
  .liediting{
    &:hover{
      .dragicon{ display: none;}
    }
  }
  .sortable-ghost{
    cursor:grab;
    .opicon{ display: none;}
  }
  .addBox {
    position: relative;
    .purifyBtnBox {
      position: absolute;
      bottom: 10px;
      right: 15px;
    }
  }
  .changeBtnBoxpos {
    position: relative;
    .feedbackBoxwai {
      padding-bottom: 20px;
      position: absolute;
      left: 0;
      top: 40px;
      width: 316px;
    }
    .feedbackBox {
      border-radius: 3px;
      opacity: 1;
      background: #FFFFFF;
      box-shadow: 0px 0px 16px 0px rgba(0, 0, 0, 0.12);
      padding: 10px;
      .feedbackBtnBox {
        display: flex;
        justify-content: space-between;
        margin-top: 10px;
        .el-button {
          border-radius: 5px!important;
          font-size: 14px;
        }
        .wthl {
          border-color: #4044ed;
          background: #4044ed;
          color: #fff;
        }
      }
    }
  }
  .changeBtnBox {
    margin: 10px 0;
    height: 24px;
    .xzyd {
      color: #4044ed;
      border-color: #4044ed;
    }
    .pagesBox {
      float: right;
      display: flex;
      margin-top: 4px;
      .pagesBtn {
        cursor: pointer;
        width: 16px;
        height: 16px;
      }
      .pagesBtnDis {
        color: #606266;
        cursor: not-allowed;
      }
    }
  }
}
#directBtn {
  border-radius: 0;
  color: #606266;
  border-color: #dcdfe6;
  background-color: #ffffff;
  float: left;
}
#filledBtn {
  border-radius: 0;
}
</style>
