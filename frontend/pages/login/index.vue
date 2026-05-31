<script setup lang="ts">
import Typed from 'typed.js'
import stats from '~/lib/stats'

definePageMeta({
  middleware: 'loginauth',
})

const typedRef = ref()
const leftRef = ref<HTMLDivElement>()
useEventListener(leftRef, 'animationend', animationEnded)

function animationEnded() {
  const typed = new Typed(typedRef.value, {
    strings: [
      '探索智能时代，高效内容生成新范式',
      '智能引证，实现内容可证、可溯源，保证内容真实性',
      '安全生成，实现内容安全可控，价值观可控引导内容安全',
      '时效性高，实现热门低时延接入，热点信息一点即达',
    ],
    typeSpeed: 100,
    backDelay: 2000,
    loop: true,
  })
}

const account = ref('')
const password = ref('')

const isAccountError = ref(false)
const accountError = ref('')

const isPasswordError = ref(false)
const passwordError = ref('')

const isLoginError = ref(false)

const isloading = ref(false)

function handleAccountBlur() {
  accountIsEmpty()
}

function handleAccountInput() {
  accountIsEmpty()
}

function accountIsEmpty() {
  if (account.value.trim().length === 0) {
    isAccountError.value = true
    accountError.value = '请输入账号'
  }
  else {
    isAccountError.value = false
    accountError.value = ''
  }
}

function handlePasswordBlur() {
  passwordIsEmpty()
}

function handlePasswordInput() {
  passwordIsEmpty()
}

function passwordIsEmpty() {
  if (password.value.trim().length === 0) {
    isPasswordError.value = true
    passwordError.value = '请输入密码'
  }
  else {
    isPasswordError.value = false
    passwordError.value = ''
  }
}

const loginErrorCount = useLocalStorage('loginErrorCount', { number: 0, time: new Date().getTime() })

async function login() {
  if (account.value.trim().length === 0) {
    isAccountError.value = true
    accountError.value = '请输入账号'
  }

  if (password.value.trim().length === 0) {
    isPasswordError.value = true
    passwordError.value = '请输入密码'
  }

  if (isAccountError.value || isPasswordError.value)
    return

  if (loginErrorCount.value.number === 10 && (new Date().getTime() - loginErrorCount.value.time < (60 * 1000 * 5))) {
    ElMessage({
      message: '登录错误次数过多，请稍后再试',
      type: 'error',
    })
    return
  }
  else if (loginErrorCount.value.number === 10 && (new Date().getTime() - loginErrorCount.value.time > (60 * 1000 * 5))) {
    loginErrorCount.value.number = 0
    loginErrorCount.value.time = new Date().getTime()
  }

  try {
    isloading.value = true
    const res = await useLogin(account.value.trim(), password.value.trim())
    if (res.error.value) {
      isLoginError.value = true
      passwordError.value = '请输入正确的密码'
      loginErrorCount.value.number += 1
    }
    else {
      loginErrorCount.value.number = 0
      loginErrorCount.value.time = new Date().getTime()
      await useFetchUser()

      if (currentUser.value?._id)
        stats.setUserId(currentUser.value?._id)

      // if (!currentUser.value?.extend_data?.has_login) {
      //   setTimeout(() => {
      //     ElMessageBox.alert('感谢您的试用，作为国内极少数【全流程国产卡部署】产品，我们目前响应速度还有点慢，但正全力优化中，再次感谢您的包容和支持~', '', {
      //       confirmButtonText: '确认',
      //       callback: () => {
      //         updateUserInfo('has_login', true)
      //       },
      //       showClose: false,
      //       customStyle: {
      //         'width': '645px !important',
      //         'padding-left': '24px !important',
      //         'padding-right': '24px !important',
      //         'padding-bottom': '24px !important',
      //         'max-width': '645px !important',
      //       },
      //     })
      //   }, 1000)
      // }

      stats.track('signin')
    }
  }
  catch (error) {

  }
  finally {
    isloading.value = false
  }
}
</script>

<template>
  <div class="relative login-container w-screen h-screen min-w-[1280px] overflow-hidden">
    <div ref="leftRef" class="absolute top-1/2 translate-y-[-79%] left">
      <p class="text-white text-[27px] leading-[1.5em] font-medium">
        智能写作助手
      </p>
      <p class="text-white text-[37px] leading-[1.75em] font-normal mt-[40px] w-[645px] h-[126px]">
        <span ref="typedRef" />
      </p>
    </div>
    <div class="right absolute top-0">
      <div class="triangle" />
      <div class="login-form relative flex flex-col bg-white items-center justify-center">
        <p class="text-[rgba(0,0,0,0.87)] text-[40px]">
          欢迎回来
        </p>
        <div
          class="input-container relative mt-[68px] mb-[36px]" :class="{
            'is-input': account.length > 0,
            'is-error': isAccountError,
          }"
        >
          <el-input
            v-model="account"
            placeholder="请输入账号"
            @blur="handleAccountBlur"
            @input="handleAccountInput"
          />
          <!-- <div class="text-error h-[24px] pl-[24px]">
            {{ accountError }}
          </div> -->
        </div>
        <div
          class="input-container mb-[24px]" :class="{
            'is-input': password.length > 0,
            'is-error': isPasswordError,
          }"
        >
          <el-input
            v-model="password"
            type="password"
            placeholder="请输入密码"
            show-password
            @input="handlePasswordInput"
            @blur="handlePasswordBlur"
          />
        </div>
        <el-button :loading="isloading" class="ll-button mt-[35px]" color="#4044ED" @click="login">
          登录
        </el-button>
        <div class="text-contact flex items-center justify-center w-full mt-[20px]">
          <span class="text-[13px] leading-[24px] text-center">反馈问题请联系 product@mail.xinyunews.cn</span>
        </div>
      </div>
      <div class="w-[96px] h-screen bg-white" />
    </div>
    <div class="w-full bg-[#05050E] absolute bottom-0 z-100 flex items-center justify-center py-[8px]">
      <span class="name ml-[4px] text-white text-[12px]">
        <NuxtLink rel="noreferrer" target="__blank" href="https://beian.miit.gov.cn">
          浙ICP备2023031265号-1
        </NuxtLink>
      </span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-container {
  background-image: url('~/assets/images/login_bg.jpg');
  background-size: cover;

  .left {
    animation: left 1s ease-in-out forwards;
  }
}

.right {
  animation: right 1s ease-in-out forwards;
  height: 100vh;
  width: calc(516px + 22.2vh);
  display: flex;
  justify-content: flex-start;
  z-index: 10;
  overflow: hidden;
  transform-origin: bottom left;

  .triangle {
    width: 0;
    height: 0;
    border-bottom: 100vh solid white;  /* 三角形的高度 */
    border-left: 22.2vh solid transparent;  /* 三角形的底边长 */
  }

  .login-form {
    width: 420px;
    height: 100vh;
  }
}

.input-container {
  &:deep(.el-input__wrapper) {
    width: 400px;
    height: 48px;
    box-sizing: border-box;
    padding: 12px 12px 12px 24px !important;
    background-color: white;
    border-radius: 5px !important;
    border: 1px solid #D9D9D9;
    box-shadow: none !important;
    input {
      color: rgba(0, 0, 0, 0.36);
      font-size: 16px;
      font-style: normal;
      font-weight: 400;
      line-height: 24px; /* 120% */
    }
  }
}

.is-input {
  &:deep(input) {
    color: rgba(0, 0, 0, 0.87) !important;
  }
}
.is-error {
  &:deep(.el-input__wrapper) {
    border: 1px solid #ED5B56;
  }
}

.text-contact {
    font-style: normal;
    font-weight: 400;
    color: rgba(0, 0, 0, 0.36);
}

.text-title {
    color: white;
    font-size: 68px;
    font-style: normal;
    font-weight: 400;
    line-height: normal;
}

.text-error {
  color: #ED5B56;
  font-size: 16px;
  font-style: normal;
  font-weight: 400;
  line-height: 24px; /* 150% */
}

.ll-button {
  width: 400px;
  height: 48px;
  padding: 12px 12px 12px 12px;
  border-radius: 10px;
  font-size: 20px;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
}

@keyframes left {
  0% {
    left: 216px;
  }
  100% {
    left: 68px
  }
}

@keyframes right {
  0% {
    right: -830px;
  }
  100% {
    right: 0px;
  }
}

.video-player {
  object-fit: cover;
  width: 100%;
  height: 100%;
}
</style>
