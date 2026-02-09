<script setup lang="ts">
import fireIcon from '~/assets/images/doc/fire.svg'

const route = useRoute()

const current = computed(() => {
  if (route.path === '/file')
    return 'file'
  else if (route.path === '/trash')
    return 'trash'
  else if (route.path === '/help')
    return 'help'
  else if ((route.path === '/search') || (route.name === 'qa-id'))
    return 'search'
  else
    return ''
})

const routes = [
  {
    path: '/search',
    name: 'AI 搜索',
    value: 'search',
    icon: 'i-ll-logo-search',
    target: '_self',
  },
  {
    path: '/file',
    name: 'AI 写作',
    value: 'file',
    icon: 'i-ll-logo-document',
    target: '_self',
    pic: fireIcon,
  },
  {
    path: 'https://dxtpeywtg9y.feishu.cn/wiki/O4xnwEor4ip9zwkcSjQcBgZznic?source_type=message&from=message',
    name: '帮助文档',
    value: 'help',
    icon: 'i-ll-logo-help',
    target: '_blank',
  },
  {
    path: '/trash',
    name: '废纸篓',
    value: 'trash',
    icon: 'i-ll-logo-dustbin',
    target: '_self',
  },
]

const isOpen = ref(true)
const asideWidth = ref(200)
const BREAK_WIDTH = 130

function handleOpen() {
  isOpen.value = !isOpen.value
  if (isOpen.value)
    asideWidth.value = 200
  else
    asideWidth.value = 92
}

watch(asideWidth, (val) => {
  if (val > BREAK_WIDTH)
    isOpen.value = true
  else
    isOpen.value = false
})

const dragLine = ref(null)
const isHoverd = useElementHover(dragLine)
let mousePositionX: null | number = null

function dragStart() {
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

  if ((asideWidth.value + offsetX) > 200)
    asideWidth.value = 200
  else if ((asideWidth.value + offsetX) < 92)
    asideWidth.value = 92
  else
    asideWidth.value += offsetX
}

function dragStop() {
  window.removeEventListener('mousemove', dragging)
}
</script>

<template>
  <aside
    class="flex shrink-0 aside box-border h-screen py-[24px] relative ease-linear transition-width"
    :class="{
      'pl-[12px]': asideWidth >= BREAK_WIDTH,
      'pl-[22px]': asideWidth < BREAK_WIDTH,
    }"
    :style="{
      minWidth: `${asideWidth}px`,
      maxWidth: `${asideWidth}px`,
      width: `${asideWidth}px`,
    }"
  >
    <div class="flex flex-col flex-1">
      <header
        class="text-aside-title pt-[24px] pb-[24px]"
        :class="{
          'pl-[15px]': asideWidth >= BREAK_WIDTH,
        }"
      >
        {{ '' }}
      </header>
      <nav class="flex-1">
        <ul>
          <li
            v-for="item in routes"
            :key="item.path"
            class="mb-[4px]"
            :class="{
              'isCurrent': current === item.value,
              'text-normal-color': current === item.value,
              'text-black-color': current !== item.value,
            }"
          >
            <NuxtLink :to="item.path" :target="item.target">
              <div
                class="flex items-center"
                :class="{
                  'p-[12px]': asideWidth >= BREAK_WIDTH,
                  'p-[15px]': asideWidth < BREAK_WIDTH,
                }"
              >
                <div :class="`${item.icon} text-[18px] shrink-0`" />
                <div v-if="asideWidth >= BREAK_WIDTH" class="text-nav-title pl-[10px] max-w-[130px] flex-1 truncate">
                  {{ item.name }}
                </div>
                <img v-if="item.pic" :src="item.pic" class="w-[16px]">
              </div>
            </NuxtLink>
          </li>
        </ul>
      </nav>
      <div
        class="shrink-0 mb-[16px] cursor-pointer flex items-center"
        :class="{
          'pl-[10px]': !isOpen,
        }"
        @click="handleOpen"
      >
        <div
          :class="{
            'i-ll-fold': isOpen,
            'i-ll-unfold': !isOpen,
          }"
        />
        <span v-if="asideWidth >= BREAK_WIDTH" class="text-[16px] font-normal leading-normal text-[#45464A] ml-[8px]">收起</span>
      </div>
      <div class="shrink-0 pt-[16px] pb-[8px]">
        <UserInfo :container-width="asideWidth" :size="asideWidth < BREAK_WIDTH ? 'small' : 'normal'" />
      </div>
    </div>
    <div
      ref="dragLine"
      class="drag-line-container shrink-0 flex items-center justify-center"
      :class="{
        'w-[12px]': asideWidth >= BREAK_WIDTH,
        'w-[22px]': asideWidth < BREAK_WIDTH,
      }"
      @mousedown.prevent="dragStart"
    >
      <div v-if="isHoverd" class="w-[1px] h-full bg-[#4044ED]" />
    </div>
  </aside>
</template>

<style lang="scss" scoped>
 .aside {
  background: #F0F2F5;
}

.text-aside-title {
    color: rgba(0, 0, 0, 0.85);
    font-size: 23px;
    font-style: normal;
    font-weight: 500;
    line-height: 22px; /* 91.667% */
}

.text-nav-title {
    font-size: 14px;
    font-style: normal;
    font-weight: 500;
    line-height: 22px; /* 157.143% */
}

.isCurrent {
    border-radius: 8px;
    background: white;
}

li:deep(a:hover) {
  text-decoration: none;
}

.drag-line-container {
  cursor: col-resize;
}
</style>
