<script setup lang="ts">
import type { QaCollectionState } from '~/store/qa'
import { QaProgressState } from '~/store/qa'

const props = defineProps<{
  data: QaCollectionState
  progress: string
  collection: QaCollectionState[]
  timeLineIndex: number
}>()

function handleMutiSubject(data: QaTimeline) {
  if (data.is_multi_subject) {
    let isR = true
    let beforeEventSubject = ''
    data.events.forEach((event, index) => {
      event.event_list.forEach((item) => {
        item.start_time_obj = time2Object(item.start_time)
        if (!beforeEventSubject) {
          beforeEventSubject = item.event_subject
          item.direc = isR ? 'right' : 'left'
        }
        else if (beforeEventSubject !== item.event_subject) {
          isR = !isR
          beforeEventSubject = item.event_subject
          item.direc = isR ? 'right' : 'left'
        }
        else if (beforeEventSubject === item.event_subject) {
          item.direc = isR ? 'right' : 'left'
        }
      })
    })
  }
}

const timeline = computed(() => {
  const p = props.data.pairs.find(item => item._id === props.data.curPairId)
  if (!p)
    return null
  if (!p.timeline_id || !p.timeline_id?.events)
    return null
  if (p.timeline_id.is_multi_subject) {
    let isR = true
    let beforeEventSubject = ''
    p.timeline_id.events.forEach((event, index) => {
      event.event_list.forEach((item) => {
        if (!beforeEventSubject) {
          beforeEventSubject = item.event_subject
          item.direc = isR ? 'right' : 'left'
        }
        else if (beforeEventSubject !== item.event_subject) {
          isR = !isR
          beforeEventSubject = item.event_subject
          item.direc = isR ? 'right' : 'left'
        }
        else if (beforeEventSubject === item.event_subject) {
          item.direc = isR ? 'right' : 'left'
        }
      })
    })
  }

  handleMutiSubject(p.timeline_id)
  return p.timeline_id
})

const { curTimelineSort: sortDir } = toRefs(props.data)
function handleSort() {
  sortDir.value = !sortDir.value
  const p = props.data.pairs.find(item => item._id === props.data.curPairId)
  if (!p)
    return
  if (!p.timeline_id || !p.timeline_id?.events)
    return

  p.timeline_id.events.sort((a, b) => {
    if (sortDir.value)
      return a.index! - b.index!

    return b.index! - a.index!
  })
  p.timeline_id.events.forEach((item) => {
    item.event_list.sort((a, b) => {
      const atime = a.start_time
      const btime = b.start_time

      if (atime.startsWith('-') && btime.startsWith('-')) {
        if (sortDir.value)
          return atime > btime ? -1 : 1
        return atime > btime ? 1 : -1
      }

      if (sortDir.value)
        return atime > btime ? 1 : -1
      return atime > btime ? -1 : 1
    })
  })
  handleMutiSubject(p.timeline_id)
}

const timelineRef = ref()
const itemScrollProgress = ref(0)
const listWrapRef = ref()
useEventListener(timelineRef, 'scroll', () => {
  const scrollTop = timelineRef.value.scrollTop
  const scrollHeight = timelineRef.value.scrollHeight
  const clientHeight = timelineRef.value.clientHeight
  let number = (scrollTop / (scrollHeight - clientHeight))

  const listHeight = listWrapRef.value?.getBoundingClientRect().height
  const min = 16 / listHeight
  if (number < min)
    number = min
  itemScrollProgress.value = number
})
let maxScroll = 1

const scrollProgress_ = computed(() => {
  let srcoll = 0

  if (!timelineRef.value)
    srcoll = 0
  else
    srcoll = itemScrollProgress.value

  if (srcoll > maxScroll)
    return maxScroll

  return srcoll
})

function isScrollable(element: HTMLElement) {
  if (!element)
    return false
  return element.scrollHeight > element.clientHeight || element.scrollWidth > element.clientWidth
}

const isScroll = ref(false)
async function initInfo() {
  await nextTick()
  const dom = document.querySelector(`.qa-last-item${props.timeLineIndex}`)
  if (dom && listWrapRef.value) {
    const height = dom.getBoundingClientRect().height + 22
    const listHeight = listWrapRef.value?.getBoundingClientRect().height
    maxScroll = 1 - height / listHeight
  }

  if (isScrollable(timelineRef.value))
    isScroll.value = true
}

watch(() => timeline.value, async (value) => {
  if (value)
    initInfo()
}, { immediate: true })

const { height } = useWindowSize()
watch(height, () => {
  initInfo()
})

const progress_ = [QaProgressState.Finish, QaProgressState.Complete, QaProgressState.TextEnd, QaProgressState.Organize]

const isNoData = computed(() => {
  if (!timeline.value && props.progress === QaProgressState.Finish)
    return true

  if (timeline.value && timeline.value.events.length === 0 && props.progress === QaProgressState.Finish)
    return true

  return false
})
const illegalCode = /\[[a-zA-Z0-9]+\]$/
function filterId(value: string) {
  return value.replace(illegalCode, '')
}
</script>

<template>
  <div
    v-if="!isNoData" class="w-full pb-[16px] max-h-[calc(100vh-56px)] h-full sticky top-[62px] flex flex-col"
  >
    <div class="flex items-center mb-[30px] justify-between w-[394px] pl-[54px] shrink-0">
      <span class="text-[16px] font-600 text-[rgba(0,0,0,0.9)]">全景时间线</span>
      <div v-if="timeline && progress_.includes(progress as QaProgressState) && timeline.events.length > 0" class="flex items-center cursor-pointer" @click="handleSort">
        <span class="text-[14px] text-[rgba(0,0,0,0.6)]">
          {{ !sortDir ? '倒序' : '顺序' }}
        </span>
        <div class="i-ll-arrow-up-down text-[16px] text-[rgba(0,0,0,0.6)]" />
      </div>
    </div>

    <template v-if="timeline && progress_.includes(progress as QaProgressState) && timeline.events.length > 0">
      <div ref="listWrapRef" class="relative flex flex-col">
        <div
          ref="timelineRef"
          class="list h-full max-h-[calc(100vh-120px)] overflow-y-scroll"
        >
          <template v-if="!timeline.is_multi_subject">
            <div
              v-for="(event, index) in timeline.events"
              :key="`${event.title}-${index}`"
              class="group"
            >
              <div
                v-if="event.title"
                class="relative w-full flex justify-start"
                :class="{
                  'group-title': index !== 0,
                  'group-title-half': index === 0,
                }"
              >
                <div class="ml-[15px] px-[10px] h-[32px] rounded-[6px] bg-[#4044ED] py-[6px] inline-block truncate text-white text-[16px] font-600">
                  {{ event.title }}
                </div>
                <div class="triangle absolute left-[5px] bottom-[10px]" />
                <img src="~/assets/images/qa/pointer.svg" class="w-[12px] h-[12px] absolute left-[-5px] top-[50%] translate-y-[-50%] timeline-icon">
                <div class="w-[5px] h-[1px] bg-[#E5E6FF] absolute left-[5px] top-[50%] translate-y-[-50%]" />
                <div />
              </div>
              <div v-if="event.title" class="w-full h-[16px] border-l border-[#E5E6FF]" />
              <div
                v-for="(item, i) in event.event_list"
                :key="`${item.event_title}-${i}`"
                class="border-[#E5E6FF] no-mutil"
                :class="{
                  'border-l': (index !== timeline.events.length - 1) || (i !== event.event_list.length - 1),
                  [`qa-last-item${timeLineIndex}`]: (index === timeline.events.length - 1) && (i === event.event_list.length - 1),
                  'last-item': (index === timeline.events.length - 1) && (i === event.event_list.length - 1),
                }"
              >
                <div class="relative pl-[15px] mb-[12px] flex items-center">
                  <span class="text-[14px] leading-[20px] text-[rgba(0,0,0,0.6)]">{{ time2String(item.start_time) }}</span>
                  <img
                    v-if="(index === timeline.events.length - 1) && (i === event.event_list.length - 1)"
                    src="~/assets/images/qa/pointer.svg" class="w-[12px] h-[12px] absolute left-[-6px] top-[50%] translate-y-[-50%] timeline-icon"
                  >
                  <img
                    v-else-if="(index === 0) && (i === 0) && !event.title"
                    src="~/assets/images/qa/pointer.svg" class="w-[12px] h-[12px] absolute left-[-6px] top-[50%] translate-y-[-50%] timeline-icon"
                  >
                  <div
                    v-else
                    class="absolute left-[-5px] top-[50%] translate-y-[-50%] timeline-icon"
                  >
                    <div class="i-ll-time text-[10px] text-[#4044ED]" />
                  </div>
                  <div class="w-[10px] h-[1px] bg-[#E5E6FF] absolute left-[5px] top-[50%] translate-y-[-50%]" />
                </div>
                <div class="w-[334px] pl-[15px] pb-[32px] overflow-hidden abs">
                  <img v-if="item.img" :src="item.img" class="w-[70px] h-[70px] rounded-[8px] overflow-hidden float-left mr-[8px] mb-[7px] object-cover">
                  <div>
                    <div class="mb-[5px] text-[15px] font-500 leading-[22px] text-[#24292F]">
                      {{ item.event_title }}
                    </div>
                    <div class="text-[13px] leading-[18px] text-[rgba(0,0,0,0.6)]" v-html="filterId(item.event_abstract_html || item.event_abstract)" />
                  </div>
                </div>
              </div>
            </div>
            <img
              v-if="isScroll"
              class="w-[10px] h-[28.67px] absolute left-[49.45px] waterDrop-img" :style="{
                top: scrollProgress_ !== 0 ? `${scrollProgress_ * 100}%` : '16px',
              }" src="~/assets/images/qa/waterDrop.png"
            >
          </template>
          <template v-else>
            <div
              v-for="(event, index) in timeline.events"
              :key="`${event.title}-${index}`"
              class="group-mutil"
            >
              <div
                v-for="(item, i) in event.event_list"
                :key="`${item.event_title}-${i}`"
                class="mutil"
                :class="{
                  [`qa-last-item${timeLineIndex}`]: (index === timeline.events.length - 1) && (i === event.event_list.length - 1),
                  'last-item': (index === timeline.events.length - 1) && (i === event.event_list.length - 1),
                }"
              >
                <div
                  class="mutil-title"
                  :class="{
                    top: (index === 0 && i === 0),
                    bottom: (index === timeline.events.length - 1 && i === event.event_list.length - 1),
                    half: (index === 0 && i === 0) || (index === timeline.events.length - 1 && i === event.event_list.length - 1),
                    full: !((index === 0 && i === 0) || (index === timeline.events.length - 1 && i === event.event_list.length - 1)),
                    right: item.direc === 'right',
                    left: item.direc === 'left',
                  }"
                >
                  <template v-if="item.direc === 'right'">
                    <div class="text text-hidden-2">
                      {{ item.event_title }}
                    </div>
                    <img v-if="item.img" class="pic ml-[8px]" :src="item.img">
                  </template>
                  <template v-else>
                    <img v-if="item.img" class="pic mr-[8px]" :src="item.img">
                    <div class="text text-hidden-2">
                      {{ item.event_title }}
                    </div>
                  </template>
                  <img
                    class="icon timeline-icon" :class="{
                      right: item.direc === 'right',
                      left: item.direc === 'left',
                    }" src="~/assets/images/qa/multi-subject.svg"
                  >
                  <div
                    v-if="item.start_time_obj" class="multi-time" :class="{
                      right: item.direc === 'right',
                      left: item.direc === 'left',
                    }"
                  >
                    <div class="year">
                      {{ item.start_time_obj.year }}
                    </div>
                    <div class="month">
                      {{ `${item.start_time_obj.month}${item.start_time_obj.day ? '.' : ''}${item.start_time_obj.day}` }}
                    </div>
                  </div>
                </div>
                <div
                  class="mutil-abs"
                  :class="{
                    my_b: !((i === event.event_list.length - 1) && (index === timeline.events.length - 1)),
                    right: item.direc === 'right',
                    left: item.direc === 'left',
                  }"
                  v-html="filterId(item.event_abstract_html || item.event_abstract)"
                />
              </div>
            </div>
            <img
              v-if="isScroll"
              class="w-[10px] h-[28.67px] absolute right-[46.5px] waterDrop-img" :style="{
                top: scrollProgress_ !== 0 ? `${scrollProgress_ * 100}%` : '16px',
              }" src="~/assets/images/qa/waterDrop.png"
            >
          </template>
        </div>
      </div>
    </template>

    <template v-else>
      <el-skeleton style="margin-left: 54px; width: 340px;" :loading="true" animated>
        <template #template>
          <el-skeleton-item
            style="width: 160px; height: 28px; margin-bottom: 12px; background:linear-gradient(270deg, rgba(229, 230, 255, 0.2) 0%, #E5E6FF 100%) !important;
"
          />
          <el-skeleton-item style="width: 340px; height: 20px; margin-bottom: 12px;" />
          <el-skeleton-item style="width: 340px; height: 20px;" />
        </template>
      </el-skeleton>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.list {
  padding-left: 54px;
  width: 394px;
  height: 100%;

  &::-webkit-scrollbar {
    display: none;
  }
  -ms-overflow-style: none;  /* IE and Edge */
  scrollbar-width: none;  /* Firefox */
}

.triangle {
  width: 0;
  height: 0;
  border: 5px solid transparent;
  border-right: 5px solid #4044ED;
}

.group-title-half::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  height: 50%; /* 控制高度 */
  border-left: 1px solid #E5E6FF;
}

.group-title::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-left: 1px solid #E5E6FF;
}

.group-mutil {
  padding: 0px 52px;
}

.mutil {
  width: 237px;
}

.mutil-title {
  width: 100%;
  display: flex;
  align-items: center;
  position: relative;
  justify-content: space-between;
  padding-bottom: 8px;

  &.right {
    justify-content: flex-end;
    padding-left: 34px;
    padding-right: 20px;
  }

  &.left {
    justify-content: flex-start;
    padding-left: 20px;
    padding-right: 34px;
  }

  &.half::before {
    content: "";
    position: absolute;
    left: 0;
    height: 50%; /* 控制高度 */
    border-left: 1px solid #E5E6FF;
  }
  &.half {
    &.top::before {
      top: 50%;
    }
    &.top::after {
      top: 50%;
    }
    &.bottom::before {
      top: 0;
    }
    &.bottom::after {
      top: 0;
    }
  }
  &.half::after {
    content: "";
    position: absolute;
    right: 0;
    top: 50%;
    height: 50%; /* 控制高度 */
    border-left: 1px solid #E5E6FF;
  }

  &.full::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    height: 100%;
    border-left: 1px solid #E5E6FF;
  }
  &.full:after {
    content: "";
    position: absolute;
    right: 0;
    top: 0;
    height: 100%;
    border-left: 1px solid #E5E6FF;
  }

  .text {
    font-size: 14px;
    font-weight: 500;
    color: #24292F;
  }

  .pic {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    overflow: hidden;
    object-fit: cover;
    flex-shrink: 0;
  }

  .icon {
    width: 20px;
    height: 20px;
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    z-index: 10;

    &.right {
      right: -9px;
    }
    &.left {
      left: -10px;
    }
  }

  .multi-time {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    width: 40px;

    .year {
      font-size: 12px;
      font-weight: 500;
      color: #24292F;
    }

    .month {
      font-size: 10px;
      color: #24292F;
    }

    &.right {
      right: -51px;

      .year {
        text-align: right
      }

      .month {
        text-align: right
      }
    }
    &.left {
      left: -51px;
    }
  }
}

.mutil-abs {
  font-size: 12px;
  line-height: 20px;
  color: rgba(0, 0, 0, 0.6);
  padding-bottom: 36px;

  &.left {
    padding-left: 20px;
    padding-right: 34px;
  }

  &.right {
    padding-left: 34px;
    padding-right: 20px;
  }

  &.my_b {
    border-left: 1px solid #E5E6FF;
    border-right: 1px solid #E5E6FF;
  }
}

.waterDrop-img {
  transition: top 0.3s linear;
}

.timeline-icon {
  z-index: 1000;
}

.mutil.last-item {
  .mutil-abs {
    padding-bottom: 0px !important;
  }
}

.no-mutil.last-item {
  .abs {
    padding-bottom: 0px !important;
  }
}
</style>
