<script setup lang="ts">
import type { FormInstance, FormRules, UploadUserFile } from 'element-plus'
import type { rowType } from '~/components/Upload2.vue'
import { NEWS_KIND, WRITE_STYLE_LIST } from '~/consts/editor'

const props = defineProps<{
  loadingVisible: boolean
  ruleForm: RuleForm
  type: string
}>()

export interface RuleForm {
  theme: string
  fileData: UploadUserFile[]
  reference: ['files']
  num?: number
  style: string
  direction: string
}

const { loadingVisible, ruleForm } = toRefs(props)
const formRef = ref<FormInstance>()

const directionRule = computed(() => {
  if (props.type === NEWS_KIND.Others) {
    return [
      { required: true, message: '请填写写作方向', trigger: 'change' },
      { min: 1, max: 200, message: '写作方向不能超过200字，请删减字数', trigger: 'change' },
    ]
  }

  return [
    { min: 1, max: 200, message: '写作方向不能超过200字，请删减字数', trigger: 'change' },
  ]
})

const rules = reactive<FormRules<RuleForm>>({
  theme: [
    { required: true, message: '请填写综述主题', trigger: 'change' },
    { min: 1, max: 100, message: '主题不能超过100字，请删减字数', trigger: 'change' },
  ],
  fileData: [
    { type: 'array', required: true, message: '请上传综述文件', trigger: 'change' },
  ],
  reference: [
    { type: 'array', required: true, message: '请选择引证生成参考范围', trigger: 'change' },
  ],
  num: [
    { validator: validateZishu, message: '请输入500~100000的整数', trigger: 'change' },
  ],
  style: [
    { required: true, message: '请选择风格', trigger: 'change' },
  ],
  direction: directionRule.value,
})

function validateZishu(rule: any, value: any, callback: any) {
  if (!value)
    callback()
  if (!/^\d*$/.test(value)) {
    callback(new Error('请输入500~100000的整数'))
    return false
  }
  if (Number.parseInt(value) < 500 || Number.parseInt(value) > 100000)
    callback(new Error('请输入500~100000的整数'))

  else
    callback()
}

const fileList = inject<Ref<UploadUserFile[]>>('step1_fileList')!

function handleUploadSuccess() {
  ruleForm.value.fileData = fileList.value
  formRef.value?.validateField('fileData')
}

function handleUploadCancel(row: rowType) {
  fileList.value = fileList.value.filter(i => i.uid !== row.data.uid)
  ruleForm.value.fileData = fileList.value
  formRef.value?.validateField('fileData')
}

function handleUploadDelete(row: rowType) {
  fileList.value = fileList.value.filter(i => i.uid !== row.data.uid)
  ruleForm.value.fileData = fileList.value
  formRef.value?.validateField('fileData')
}

const activeNames = ref([])

function checkClick() {
  window.open('https://www.cac.gov.cn/2021-10/18/c_1636153133379560.htm', '_blank')
}

const directionPlaceHolderMap = {
  [NEWS_KIND.Message]: '例如：请侧重描写“村超”对于乡村振兴的意义',
  [NEWS_KIND.Communication]: '例如：行文重点请偏向描摹抗灾救灾中的感人事迹',
  [NEWS_KIND.ExclusiveInterview]: '例如：请侧重描写关于AI安全与准确性的内容',
  [NEWS_KIND.Feature]: '例如：请重点描写普京访问哈工大和师生交流的场景',
  [NEWS_KIND.Others]: '例如：请根据素材生成一篇非虚构写作',
}

const directionPlaceHolder = computed(() => directionPlaceHolderMap[props.type])
const fileLabel = computed(() => {
  if (props.type === NEWS_KIND.Summarize)
    return '上传综述文件'
  else
    return '上传素材'
})

const baseURL = import.meta.env.VITE_API
const uploadUrl = ref(`${baseURL}/api/material/upload`)

defineExpose({
  formRef,
})
</script>

<template>
  <div class="pt-[16px]">
    <el-form
      v-if="!loadingVisible"
      ref="formRef"
      style="margin: 16px;"
      :model="ruleForm"
      :rules="rules"
      label-width="auto"
      label-position="top"
      status-icon
    >
      <el-form-item v-if="props.type === NEWS_KIND.Summarize" label="综述主题" prop="theme" class="them_tit">
        <el-input
          v-model="ruleForm.theme"
          placeholder="例如：各地文旅部门积极发挥主观能动性挖掘新特色"
        />
      </el-form-item>
      <el-form-item :label="fileLabel" prop="fileData" class="them_tit">
        <Upload2
          v-model:file-list="fileList"
          size="small"
          :action="uploadUrl"
          @success="handleUploadSuccess"
          @cancel="handleUploadCancel"
          @delete="handleUploadDelete"
        >
          <el-button class="btnupload">
            <div class="i-ll-upload text-[16px] mt-[3px]" />
            本地上传
          </el-button>
        </Upload2>
      </el-form-item>
      <el-form-item v-if="props.type !== NEWS_KIND.Summarize" label="写作方向要求" prop="direction" class="them_tit">
        <el-input
          v-model="ruleForm.direction"
          :placeholder="directionPlaceHolder"
        />
      </el-form-item>
      <el-collapse v-model="activeNames" class="morecoll">
        <el-collapse-item title="更多选项" name="1">
          <el-form-item label="引证生成参考范围" prop="reference">
            <el-checkbox-group v-model="ruleForm.reference">
              <el-checkbox value="files" name="reference" disabled>
                上传文件
              </el-checkbox>
              <el-checkbox value="sites" name="reference" class="txt_name">
                可信网站
              </el-checkbox>
            </el-checkbox-group>
            <div class="check" @click="checkClick">
              查看清单
            </div>
          </el-form-item>
          <el-form-item label="写作风格" prop="style">
            <div class="w-[160px]">
              <el-select v-model="ruleForm.style">
                <el-option v-for="item in WRITE_STYLE_LIST" :key="item.type" :label="item.title" :value="item.type" />
              </el-select>
            </div>
          </el-form-item>
          <!-- <el-form-item label="字数要求" prop="num">
            <el-input v-model.number="ruleForm.num" controls-position="right" style="width: 160px;text-align: left;" />
          </el-form-item> -->
        </el-collapse-item>
      </el-collapse>
    </el-form>
  </div>
</template>

<style lang="scss" scoped>
::v-deep .morecoll{
   border-top: none; border-bottom: none;
   .el-collapse-item__wrap{
    border-bottom:none;
   }
  .el-collapse-item__header{
     border-bottom:none; display: block; text-align:left;
    i{ margin-left: 3px;;}
  }
  .el-collapse-item__arrow{
    transform: rotate(90deg);
  }
  .el-collapse-item__arrow.is-active{
    transform: rotate(-90deg);
  }
  .txt_name{
    color: rgba(0, 0, 0, 0.9);
    .el-checkbox__input.is-checked+.el-checkbox__label{
      color: rgba(0, 0, 0, 0.9)
    }
  }
}

.check {
  cursor: pointer;
  color: #4044ed;
  margin-left: 10px;
}
</style>
