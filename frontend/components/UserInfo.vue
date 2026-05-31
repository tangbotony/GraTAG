<script setup lang="ts">
const props = defineProps<{
  containerWidth: number
  size: string
}>()

const firstLetter = computed(() => {
  if (currentUser.value?.name)
    return currentUser.value?.name[0].toLowerCase()
  return currentUser.value?.email[0].toLowerCase()
})

const colors = [
  '#FA541C',
  '#FA8C16',
  '#FAAD14',
  '#FAAD14',
  '#FAAD14',
  '#722ED1',

  '#4044ED',
  '#1677FF',
  '#2F54EB',
  '#2F54EB',

  '#4044ED',
  '#1677FF',
  '#2F54EB',
  '#2F54EB',

  '#4044ED',
  '#1677FF',
  '#2F54EB',
  '#2F54EB',
]

const color = colors[Math.floor(Math.random() * colors.length)]

const dialogVisible = ref(false)

function logout() {
  useLogout()
  currentUserLocalStorage.value = null
  dialogVisible.value = false
}

const stack = ref<string[]>(['user'])
const current = computed(() => stack.value[stack.value.length - 1])

const dialogTitle = computed(() => {
  if (current.value === 'user')
    return '账户'
  else if (current.value === 'username')
    return '修改用户名'
})

const username = ref('')
function saveUsername() {
  dialogVisible.value = false
}

watch(dialogVisible, (val) => {
  if (!val) {
    stack.value = ['user']
    username.value = ''
  }
})
</script>

<template>
  <div
    class="flex items-center cursor-pointer w-full"
    @click="dialogVisible = true"
  >
    <div
      :style="{
        backgroundColor: color,
      }"
      class="rounded-full w-[36px] h-[36px] my-[3px] flex items-center justify-center text-letter shrink-0  text-white"
    >
      {{ firstLetter?.toLocaleUpperCase() }}
    </div>
    <Transition name="userinfo">
      <div
        v-if="props.size !== 'small'"
        class="flex-1 pl-[8px]"
        :style="{
          maxWidth: `${props.containerWidth - 36 - 8 - 24}px`,
        }"
      >
        <div
          class="truncate text-[14px] font-normal leading-normal text-[rgba(0,0,0,0.9)]"
        >
          {{ currentUser?.name }}
        </div>
        <div class="truncate max-w-[132px] text-[14px] font-normal leading-normal text-[rgba(0,0,0,0.6)]">
          {{ currentUser?.email }}
        </div>
      </div>
    </Transition>
  </div>
  <el-dialog
    v-model="dialogVisible"
    :width="425"
    append-to-body
  >
    <template #header>
      <div class="flex items-center">
        <div v-if="stack.length > 1" class="i-ll-back text-[20x] mr-[4px] cursor-pointer" @click="stack.pop()" />
        <span class="text-dialog-title">{{ dialogTitle }}</span>
      </div>
    </template>
    <div v-if="current === 'user'" class="py-[30px]">
      <div class="flex items-center justify-between item">
        <div class="flex items-center">
          <div class="i-ll-username text-[20px] text-[#D9D9D9]" />
          <span class="text-title ml-[4px]">用户名</span>
        </div>
        <div class="text-gray-color text-operation">
          <span class="mr-[40px]">{{ currentUser?.name || '无名' }}</span>
          <span class="cursor-not-allowed">修改</span>
        </div>
      </div>
      <div class="flex items-center justify-between item">
        <div class="flex items-center">
          <div class="i-ll-avatar text-[20px] text-[#D9D9D9]" />
          <span class="text-title ml-[4px]">头像</span>
        </div>
        <div class="text-gray-color text-operation flex items-center">
          <div
            :style="{
              backgroundColor: color,
            }"
            class="rounded-full w-[24px] h-[24px] flex items-center justify-center text-white mr-[40px] inline-block text-letter"
          >
            {{ firstLetter?.toLocaleUpperCase() }}
          </div>
          <span class="cursor-not-allowed">修改</span>
        </div>
      </div>
      <div class="flex items-center justify-between item">
        <div class="flex items-center">
          <div class="i-ll-mail text-[20px] text-[#D9D9D9]" />
          <span class="text-title ml-[4px]">邮箱</span>
        </div>
        <div class="text-gray-color text-operation">
          <span class="mr-[40px]">{{ currentUser?.email || "未设置" }}</span>
          <span class="cursor-not-allowed">修改</span>
        </div>
      </div>
      <div class="flex items-center justify-between item">
        <div class="flex items-center">
          <div class="i-ll-password text-[20px] text-[#D9D9D9]" />
          <span class="text-title ml-[4px]">密码</span>
        </div>
        <div class="text-gray-color text-operation">
          <span class="mr-[40px]">*******</span>
          <span class="cursor-not-allowed">修改</span>
        </div>
      </div>
    </div>
    <div v-else-if="current === 'username'" class="w-full h-[334px]">
      <div class="w-full">
        <el-input
          v-model="username"
          maxlength="20"
          show-word-limit
          type="text"
          placeholder="请输入用户名"
        />
      </div>
    </div>
    <template #footer>
      <div v-if="current === 'user'" class="button-container">
        <el-button @click="logout">
          退出登录
        </el-button>
      </div>
      <el-button v-else-if="current === 'username'" :disabled="username.length === 0" @clock="saveUsername">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
.text-letter {
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  line-height: 24px;
  text-align: center;
}

.text-title {
  color: var(--c-text-black, rgba(0, 0, 0, 0.85));
  font-size: 14px;
  font-style: normal;
  font-weight: 400;
  line-height: 22px; /* 157.143% */
}

.text-operation {
  color: rgba(0, 0, 0, 0.45);
  font-size: 13px;
  font-style: normal;
  font-weight: 400;
  line-height: 20px; /* 153.846% */
}

.item {
  height: 72px;
}

.item:not(:last-child) {
  box-shadow: 0px -1px 0px 0px #F0F0F0 inset;
}

.button-container {
  &:deep( button ) {
    background: rgba(0, 0, 0, 0.10) !important;
    color: rgba(0, 0, 0, 0.85) !important;
    border: 1px solid rgba(0, 0, 0, 0.10) !important;
    text-align: center;
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px; /* 157.143% */
  }
}

.text-dialog-title {
  color: var(--c-text-black, rgba(0, 0, 0, 0.85));
  font-size: 16px;
  font-style: normal;
  font-weight: 500;
  line-height: 24px; /* 150% */
}
</style>

<style>
.userinfo-enter-active {
  transition: opacity 0.5s ease;
}

.userinfo-enter-from,
.userinfo-leave-to {
  opacity: 0;
}
</style>
