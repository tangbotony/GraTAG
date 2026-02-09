<script setup lang="ts">
import type { QuoteEditor } from '~/composables/quote'

const props = defineProps<{
  id: string
  content: string
  title: string
  plainText: string
}>()

const lastestContentSaved = ref(props.content)
const lastestTitleSaved = ref(props.title)

const datelastSaved = ref<null | Date>(null)
const dateFormat = computed(() => {
  if (!datelastSaved.value)
    return ''
  return `${formatDateNumber(datelastSaved.value.getHours())}:${formatDateNumber(datelastSaved.value.getMinutes())}`
})
const isSaving = ref(false)

async function save() {
  if (props.id && (props.content || props.title)) {
    datelastSaved.value = new Date()
    isSaving.value = true
    const text = props.content
    const name = props.title
    const plainText = props.plainText
    const reference = quoteState.quotes.map((quote: QuoteEditor) => {
      const quote_: Record<string, string> = {}
      if (quote.href && currentArticle.referenceContent.has(quote.href)) {
        const content = currentArticle.referenceContent.get(quote.href)!
        quote_.content = content
      }
      return {
        title: quote.title || '',
        description: quote.description || '',
        url: quote.href || '',
        id: quote_.id || '',
        content: quote_.content || '',
      }
    })
    await useFileUpdate({ id: props.id, text, name, plain_text: plainText, reference })
    isSaving.value = false
    lastestContentSaved.value = text
    lastestTitleSaved.value = name
  }
}

useIntervalFn(() => {
  if (!isSaving.value) {
    const text = props.content
    const name = props.title
    if (text === lastestContentSaved.value && name === lastestTitleSaved.value)
      return

    save()
  }
}, 1000 * 30)

const keys = useMagicKeys()
const CtrlS = keys['Ctrl+S']
const CommandS = keys['Command+S']
watch([CtrlS, CommandS], (val) => {
  if (val[0] || val[1])
    save()
})

if (isWindows()) {
  useEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 's')
      e.preventDefault()
  })
}

if (isMac()) {
  useEventListener('keydown', (e) => {
    if (e.metaKey && e.key === 's')
      e.preventDefault()
  })
}

useEventListener('beforeunload', (e) => {
  if (lastestContentSaved.value !== props.content || lastestTitleSaved.value !== props.title) {
    e.preventDefault()

    e.returnValue = ''

    const confirmationMessage = '确定要离开此页面吗？';
    (e || window.event).returnValue = confirmationMessage // 兼容旧版浏览器

    return confirmationMessage
  }
})

const router = useRouter()
let isSure = false
router.beforeEach((to, from, next) => {
  if (from.name === 'document-edit' && !isSure) {
    if (lastestContentSaved.value !== props.content || lastestTitleSaved.value !== props.title) {
      ElMessageBox.confirm('修改未保存，是否离开？', '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }).then(() => {
        isSure = true
        navigateTo(to.path)
      }).catch(() => {
        isSure = false
      })
      next(false)
      return
    }
  }
  next()
})
</script>

<template>
  <div class="flex items-center">
    <div class="mr-[20px] flex items-center">
      <template v-if="datelastSaved && !isSaving">
        <div class="i-ll-edit-check text-[16px] text-gray-lighter-color mr-[4px]" />
        <span class="text-save">最近保存：{{ dateFormat }}</span>
      </template>
      <template v-else-if="isSaving">
        <span class="text-save">保存中...</span>
      </template>
    </div>
    <el-tooltip
      content="保存"
    >
      <div class="i-ll-edit-save cursor-pointer text-[16px] text-gray-lighter-color" @click="save" />
    </el-tooltip>
  </div>
</template>

<style lang="scss" scoped>
.text-save {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
}
</style>
