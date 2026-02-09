<script setup lang="ts">
import type { FormInstance, FormRules } from 'element-plus'
import md5 from 'md5'

definePageMeta({
  middleware: ['auth', 'admin'],
  name: 'admin',
})

const dialogVisible = ref(false)
const dialogState = ref('')
const formRef = ref<FormInstance | null>(null)
const formData = reactive<{
  name: string
  passwd: string
  department: string
  real_name: string
  phone: string
  date: [string, string]
  max_devices: string
  passwd_update: string
  remark: string
}>({
  name: '',
  passwd: '',
  department: '',
  real_name: '',
  phone: '',
  date: ['', ''],
  max_devices: '',
  passwd_update: '',
  remark: '',
})

const currentId = ref('')

function updateUser(value: User) {
  formData.passwd_update = ''
  formData.name = value.name
  formData.department = value.department
  formData.real_name = value.real_name || ''
  formData.phone = value.phone || ''
  formData.date = [value.create_date, value.expire_date] || []
  formData.max_devices = `${value.max_devices}` || '1'
  formData.remark = value.remark || ''
  currentId.value = value._id
  dialogState.value = 'update'
  dialogVisible.value = true
}

function addUser() {
  dialogState.value = 'add'
  dialogVisible.value = true
}

const { data, refresh, pending } = useListUsers()

const tableData = computed(() => {
  if (!data.value)
    return []

  data.value.res.sort((i, j) => {
    if (!j.create_date && i.create_date)
      return -1
    return i.create_date > j.create_date ? -1 : 1
  })
  return data.value.res
})

interface RuleForm {
  name: string
  passwd: string
  date: string[]
  department: string
  real_name: string
  phone: string
  max_devices: number
  passwd_update: string
}

const rules = reactive<FormRules<RuleForm>>({
  name: [
    { required: true, message: '请输入账号名', trigger: 'blur' },
    { max: 50, message: '不得超过50个字符', trigger: 'change' },
    {
      validator: (rule, value, callback) => {
        if (!/^[a-zA-Z0-9]+$/.test(value) && dialogState.value === 'add')
          callback(new Error('只能包含英文字母，数字'))

        else
          callback()
      },
      trigger: 'change',
    },
  ],
  passwd: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { max: 50, message: '不得超过50个字符', trigger: 'change' },
    {
      validator: (rule, value, callback) => {
        if (!/^[a-zA-Z0-9]+$/.test(value))
          callback(new Error('只能包含英文字母，数字'))

        else
          callback()
      },
      trigger: 'change',
    },
  ],
  passwd_update: [
    { max: 50, message: '不得超过50个字符', trigger: 'change' },
    {
      validator: (rule, value, callback) => {
        if (!value)
          callback()

        if (!/^[a-zA-Z0-9]+$/.test(value))
          callback(new Error('只能包含英文字母，数字'))

        else
          callback()
      },
      trigger: 'change',
    },
  ],
  department: [
    { required: true, message: '请输入所属单位', trigger: 'change' },
    { max: 100, message: '不得超过100个字符', trigger: 'change' },
  ],
  real_name: [
    { max: 100, message: '不得超100个字符', trigger: 'change' },
  ],
  phone: [
    {
      validator: (_, value: string, callback: (val?: any) => void) => {
        if (value && !/\d{11}/.test(value))
          callback(new Error('请输入11位手机号'))

        else
          callback()
      },
      trigger: 'change',
    },
  ],
  max_devices: [
    { required: true, message: '请输入设备数', trigger: 'blur' },
    {
      validator: (_, value: string, callback: (val?: any) => void) => {
        const num = Number.parseInt(value.toString())
        if (Number.isNaN(num))
          callback(new Error('请输入数字'))

        else if (num < 1 || num > 100)
          callback(new Error('请输入1-100的数字'))

        else
          callback()
      },
      trigger: 'change',
    },
  ],
  date: [
    { required: true, message: '请选择时段', trigger: 'blur' },
    {
      validator: (_, value: string[], callback: (val?: any) => void) => {
        if (!value || !value.length)
          callback(new Error('请选择时段'))

        if (value.length !== 2 || !value[0] || !value[1])
          callback(new Error('请选择时段'))
        else
          callback()
      },
      trigger: 'blur',
    },
  ],
})

function handleBeforeDialogClose() {
  resetform()
  dialogVisible.value = false
  currentId.value = ''
}

async function submit() {
  if (!formRef.value)
    return
  await formRef.value.validate(async (valid, fields) => {
    if (valid) {
      if (dialogState.value === 'add') {
        const { error } = await useAddUser({
          name: formData.name,
          passwd: md5(formData.passwd),
          department: formData.department,
          real_name: formData.real_name,
          phone: formData.phone,
          create_date: formData.date[0] as string,
          expire_date: formData.date[1] as string,
          max_devices: Number.parseInt(formData.max_devices),
          remark: formData.remark,
        })
        if (!error.value) {
          ElMessage.success('新增成功')
          refresh()
        }
        if (error.value)
          return
      }
      else {
        const data: any = {
          _id: currentId.value,
          department: formData.department,
          real_name: formData.real_name,
          phone: formData.phone,
          create_date: formData.date[0] as string,
          expire_date: formData.date[1] as string,
          max_devices: Number.parseInt(formData.max_devices),
          remark: formData.remark,
        }
        if (formData.passwd_update)
          data.passwd = md5(formData.passwd_update)

        const { error } = await useUpdateUser(data)
        if (!error.value) {
          refresh()
          ElMessage.success('编辑成功')
        }
        if (error.value)
          return
      }

      resetform()
      dialogVisible.value = false
      currentId.value = ''
    }
  })
}

function resetform() {
  if (formRef.value)
    formRef.value.resetFields()
  formData.name = ''
  formData.passwd = ''
  formData.department = ''
  formData.real_name = ''
  formData.phone = ''
  formData.date = ['', '']
  formData.passwd_update = ''
  formData.remark = ''
  formData.max_devices = '1'
}

function handleMaxDevicesChange(value: string) {
  if (!value) {
    formData.max_devices = ''
    return
  }
  const num = Number.parseInt(value.toString())
  if (Number.isNaN(num))
    return

  formData.max_devices = `${num}`
}
</script>

<template>
  <div class="w-screen h-screen p-5 overflow-y-scroll">
    <div>
      <el-button class="mb-[16px]" @click="addUser">
        新增体验账号
      </el-button>
    </div>
    <el-table
      v-loading="pending"
      size="small"
      :data="tableData"
      style="width: 100%"
      row-key="_id"
    >
      <el-table-column prop="name" label="账号名" width="180" />
      <el-table-column label="试用时段" width="240">
        <template #default="scope">
          <div v-if="scope.row.create_date && scope.row.expire_date">
            {{ `${scope.row.create_date}-${scope.row.expire_date}` }}
          </div>
          <div v-else>
            永久有效
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="department" label="所属单位" width="180" />
      <el-table-column prop="real_name" label="真实姓名" width="100" />
      <el-table-column prop="phone" label="手机号" width="100" />
      <el-table-column prop="max_devices" label="可登录设备数" width="100" />
      <el-table-column prop="creator" label="创建人" width="150" />
      <el-table-column prop="remark" label="备注" width="120" />
      <el-table-column label="操作" width="80">
        <template #default="scope">
          <el-button size="small" @click="updateUser(scope.row)">
            编辑
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog
      v-model="dialogVisible"
      :title="dialogState === 'add' ? '新增体验账号' : '编辑体验账号'"
      :before-close="handleBeforeDialogClose"
    >
      <div class="p-4">
        <el-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          :label-width="100"
        >
          <el-form-item label="账号名" prop="name">
            <template v-if="dialogState !== 'update'">
              <el-input v-model="formData.name" />
            </template>
            <template v-else>
              <div class="text-gray-500">
                {{ formData.name }}
              </div>
            </template>
          </el-form-item>
          <el-form-item v-if="dialogState !== 'update'" label="密码" prop="passwd">
            <el-input v-model="formData.passwd" />
          </el-form-item>
          <el-form-item v-else label="密码" prop="passwd_update">
            <el-input v-model="formData.passwd_update" />
          </el-form-item>
          <el-form-item label="所属单位" prop="department">
            <el-input v-model="formData.department" />
          </el-form-item>
          <el-form-item label="真实姓名" prop="real_name">
            <el-input v-model="formData.real_name" />
          </el-form-item>
          <el-form-item label="手机号" prop="phone">
            <el-input v-model="formData.phone" />
          </el-form-item>
          <el-form-item label="最大设备数" prop="max_devices">
            <el-input :model-value="formData.max_devices" :precision="0" :min="1" :max="100" @update:model-value="handleMaxDevicesChange" />
          </el-form-item>
          <el-form-item label="试用时段" prop="date">
            <el-date-picker
              v-model="formData.date"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
            />
          </el-form-item>
          <el-form-item label="备注" prop="remark">
            <el-input v-model="formData.remark" />
          </el-form-item>
          <el-form-item>
            <div class="flex justify-end w-full">
              <el-button type="primary" @click="submit">
                {{ dialogState === 'add' ? '新增' : '编辑' }}
              </el-button>
            </div>
          </el-form-item>
        </el-form>
      </div>
    </el-dialog>
  </div>
</template>
