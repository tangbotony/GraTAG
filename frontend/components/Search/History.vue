<script lang="ts" setup>
const $emits = defineEmits<{
  (e: 'change', count: number): void
}>()
const { data, error, refresh, pending } = useGetQaHistory()
interface RecordType { type: string; text: string; data: QaHistoryRecord[] }
const record = computed(() => {
  if (error.value || data.value?.results === undefined)
    return []
  if (data.value.results.length === 0)
    return []

  const today: RecordType = {
    data: [],
    type: 'today',
    text: '今天',
  }
  const yesterday: RecordType = {
    data: [],
    type: 'yesterday',
    text: '昨天',
  }
  const before7: RecordType = {
    data: [],
    type: 'before7',
    text: '过去7天',
  }
  const before30: RecordType = {
    data: [],
    type: 'before30',
    text: '过去30天',
  }

  data.value.results.filter(i => !!i.title).forEach((item) => {
    const date = new Date(item.create_time)
    const now = new Date()
    const today24 = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 24, 0, 0)
    const diff = today24.getTime() - date.getTime()
    const diffDays = diff / (1000 * 60 * 60 * 24)
    if (diffDays <= 1)
      today.data.push(item)
    else if (diffDays <= 2)
      yesterday.data.push(item)
    else if (diffDays <= 7)
      before7.data.push(item)
    else
      before30.data.push(item)
  })
  today.data.sort((x, y) => {
    return new Date(y.create_time).getTime() - new Date(x.create_time).getTime()
  })
  yesterday.data.sort((x, y) => {
    return new Date(y.create_time).getTime() - new Date(x.create_time).getTime()
  })
  before7.data.sort((x, y) => {
    return new Date(y.create_time).getTime() - new Date(x.create_time).getTime()
  })
  before30.data.sort((x, y) => {
    return new Date(y.create_time).getTime() - new Date(x.create_time).getTime()
  })
  const res = [today, yesterday, before7, before30]
  return res.filter(item => item.data.length > 0)
})

watch(record, (val) => {
  $emits('change', val.length)
})

const popoverVisible = ref(false)
const virtualBtn = ref()
const popoverContentRef = ref()

let lastestClickItem: QaHistoryRecord | undefined
let lastestType: 'del' | undefined
const currentRecord = ref<QaHistoryRecord | null>(null)

async function closePopover() {
  popoverVisible.value = false
  await nextTick()
  virtualBtn.value = undefined
  lastestClickItem = undefined
  lastestType = undefined
  currentRecord.value = null
}
async function handlePopoverVisible(event: Event, r: QaHistoryRecord, type: 'del') {
  event.stopPropagation()
  virtualBtn.value = event.currentTarget
  currentRecord.value = r

  if (!lastestClickItem || !lastestType) {
    lastestClickItem = r
    lastestType = type
    popoverVisible.value = true
  }
  else {
    if (lastestClickItem._id !== r._id || lastestType !== type) {
      lastestClickItem = r
      lastestType = type
      popoverVisible.value = true
    }
    else {
      closePopover()
    }
  }
}

const popoverContentContainerRef = computed(() => {
  if (!popoverContentRef.value)
    return null
  const element = popoverContentRef.value as HTMLElement
  return element.parentElement
})

onClickOutside(popoverContentContainerRef, async (event: Event) => {
  const target = event.target as HTMLElement
  if (target.dataset.type === 'search-history-del')
    return
  closePopover()
})

async function ok() {
  const id = currentRecord.value?._id
  closePopover()
  if (lastestType === 'del' && id) {
    await useDeleteQaSeriesDelete(id)
    await refresh()
  }
}

function goQa(item: QaHistoryRecord) {
  window.open(`/qa/${item._id}`, '_blank')
}
</script>

<template>
  <div v-if="pending" class="flex justify-center">
    <img
      :style="{ width: '24px' }"
      src="~/assets/images/generate/generate-loading.png"
    >
  </div>
  <div v-if="!pending && record.length === 0" class="flex justify-center text-[14px] text-[#666]">
    {{ error ? '加载失败' : '暂无搜索记录' }}
  </div>
  <div
    v-for="(item) in record"
    :key="item.type"
    class="mb-[24px]"
  >
    <div class="text-[14px] font-normal leading-[20px] mb-[12px] text-[rgba(0,0,0,0.4)]">
      {{ item.text }}
    </div>
    <div
      v-for="r in item.data"
      :key="r._id"
      class="record flex items-center justify-between p-[12px] border border-[#D9D9D9] hover:border-[#4044ED] rounded-[8px] mb-[12px] cusor-pointer"
      @click="goQa(r)"
    >
      <div class="truncate text-[14px] font-normal leading-normal text-[rgba(0,0,0,0.9)]">
        {{ r.title }}
      </div>
      <div class="flex items-center shrink-0">
        <div
          v-if="r.is_subscribe" class="rounded-[20px] bg-[#E5E6FF] py-[2px] px-[6px] text-[10px] font-normal leading-normal text-[#4044ED]"
        >
          已订阅
        </div>
        <div
          data-type="search-history-del"
          class="record-delete ml-[8px] i-ll-edit-delete text-[16px] cursor-pointer text-[rgba(0,0,0,0.45)]"
          :class="{
            'is-edit': currentRecord?._id === r._id,
          }"
          @click="handlePopoverVisible($event, r, 'del')"
        />
      </div>
    </div>
  </div>
  <el-popover
    :width="200"
    :visible="popoverVisible"
    :virtual-ref="virtualBtn"
    virtual-triggering
  >
    <div ref="popoverContentRef" class="w-full">
      <div class="text-[14px] font-500 leading-[22px]">
        确认删除这个问答吗？
      </div>
      <div class="flex items-center justify-end mt-[16px]">
        <el-button class="!bg-[#E7E7E7] !hover:border-transparent" size="small" @click="closePopover">
          取消
        </el-button>
        <el-button type="primary" size="small" @click="ok">
          确认
        </el-button>
      </div>
    </div>
  </el-popover>
</template>

<style lang="scss" scoped>
.record {
    &-delete {
        display: none;
    }

    &:hover .record-delete {
        display: block;
    }

    .is-edit.record-delete {
        display: block !important;
    }
}
</style>
