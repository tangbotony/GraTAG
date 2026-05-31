<script setup lang="ts">
import { EditorContent } from '@tiptap/vue-3'
import type { EditorEvents } from '@tiptap/vue-3'
import { WRITE_KIND } from '~/consts/editor'
import type { QuoteRef } from '~/composables/api/file'

const DocTitleAsync = defineAsyncComponent(() => import('~/components/Doc/Title.vue'))
const DocPolishWriteOldAsync = defineAsyncComponent(() => import('~/components/Doc/PolishWriteOld.vue'))
const DocExpandWriteAsync = defineAsyncComponent(() => import('~/components/Doc/ExpandWrite.vue'))
const DocContinueWriteAsync = defineAsyncComponent(() => import('~/components/Doc/Continue/Write.vue'))

definePageMeta({
  middleware: 'auth',
  name: 'document-edit',
})
const route = useRoute()
onBeforeMount(() => {
  resetQuoteState()
})

const isCreated = ref(false)
const { editor } = useTiptap({
  content: currentArticle.content,
  onUpdate: ({ editor }: EditorEvents['update']) => {
    const html = editor.getHTML()
    currentArticle.content = html
    currentArticle.plainText = editor.getText()
    updateQuotesByHtml(html, currentArticle)
  },
  onCreate: () => {
    isCreated.value = true
  },
})

const isloading = ref(false)
onMounted(async () => {
  isloading.value = true
  const { data } = await useFile(route.params.id as string)
  if (data.value?.doc) {
    currentArticle.title = data.value.doc.name
    currentArticle.content = data.value.doc.text
    currentArticle.path = data.value.doc.path
    currentArticle.isQuote = data.value.doc.is_quote
    currentArticle.doc = data.value.doc
    data.value.doc.reference?.forEach((quote: QuoteRef) => {
      currentArticle.referenceContent.set(quote.url, quote.content)
    })

    editor.value?.commands.insertContent(data.value.doc.text)
    editor.value?.commands.focus(1)
  }
  isloading.value = false
  isArticleInit.value = true
  initGenNews()
})

function initGenNews() {
  const data = sessionStorage.getItem('qa-temp-gen-new')
  if (!data)
    return

  handleCurrentAi('generate')
}

onUnmounted(() => {
  initArticleState()
})

const currentAI = ref('')
const currentAIStyle = ref('')
provide('currentAIStyle', currentAIStyle)
const currentWritingCom = ref()
const visibleRightSideBar = ref(false)
const isMiniEditorWindow = computed(() => {
  return visibleRightSideBar.value || !!quoteState.currentQuote
})

function checkNumberWords(type: string) {
  if (type === WRITE_KIND.Title && currentArticle.plainText.length < 128) {
    ElMessage({
      message: '正文内容超过128个字才可自动生成标题哦～',
      type: 'warning',
    })
    return false
  }

  if (type === WRITE_KIND.Title && currentArticle.plainText.length >= 3000) {
    ElMessage({
      message: '正文内容超过3000个字，不支持生成标题哦～',
      type: 'warning',
    })
    return false
  }

  return true
}

async function handleCurrentAi(val: string, isFromBubble = false, style?: string) {
  if (!editor.value)
    return

  if (!checkNumberWords(val))
    return

  if (isFromBubble && !editor.value.state.selection.empty) {
    editor.value.commands.correctBoundary()
    selectCurrentSelectionSentence(editor.value)
  }

  currentWritingCom.value?.clear(!isFromBubble)
  // wait the end of before req
  await sleep(0)

  currentAI.value = val
  if (style)
    currentAIStyle.value = style
  visibleRightSideBar.value = true
  await nextTick()

  // wait async component
  while (!currentWritingCom.value)
    await sleep(0)

  currentWritingCom.value?.init()
}

function handleAiClose() {
  visibleRightSideBar.value = false
  currentAI.value = ''
  editor.value?.commands.focus()
  currentAIStyle.value = ''
}

function handleAiHide() {
  visibleRightSideBar.value = false
}

function handleAiShow() {
  visibleRightSideBar.value = true
}

const scrollcontainer = ref()

const visibleGuideBoard = computed(() => {
  return currentArticle.plainText.length === 0 && !currentArticle.content.includes('img') && !isloading.value && !currentAI.value
})

const inputArticleTitle = ref()

function handleNavi(kind: string, style?: string) {
  handleCurrentAi(kind, false, style)
}

function handleEditorBubbleMenuChange(val: string) {
  const val_ = val.split('-')
  handleCurrentAi(val_[0], true, val_[1])
}

useEventListener('beforeunload', (e) => {
  if (currentAI.value) {
    e.preventDefault()

    e.returnValue = ''

    const confirmationMessage = '确定要离开此页面吗？';
    (e || window.event).returnValue = confirmationMessage // 兼容旧版浏览器
    return confirmationMessage
  }
})

onBeforeMount(() => {
  Promise.all([
    () => import('~/components/Doc/Title.vue'),
    () => import('~/components/Doc/PolishWriteOld.vue'),
    () => import('~/components/Doc/ExpandWrite.vue'),
    () => import('~/components/Doc/Continue/Write.vue'),
  ])
})
</script>

<template>
  <div
    class="h-full w-full min-w-[1280px] flex flex-col relative overflow-hidden"
  >
    <DocNavi :current-article="currentArticle" :current-a-i="currentAI" :is-init="isArticleInit" @current-ai-change="handleNavi" />
    <EditorToolbar v-if="editor" :editor="editor" />
    <div class="w-full h-[calc(100vh-85px)] flex relative">
      <EditorOutline :editor="editor" :title="currentArticle.title" :container="scrollcontainer" />
      <div class="flex-1 h-[calc(100vh-85px)] relative">
        <div ref="scrollcontainer" class="scrollcontainer h-full w-full flex justify-center relative pt-[48px] px-[42px] overflow-y-scroll">
          <div
            class="flex flex-col items-center w-full"
            :class="{
              'max-w-[1068px]': !isMiniEditorWindow,
              'max-w-[812px]': isMiniEditorWindow,
            }"
          >
            <el-skeleton style="width: 812px" :loading="isloading" animated>
              <template #template>
                <el-skeleton-item variant="p" style="width: 166px; height: 40px; margin-top: 16px;" />
              </template>
              <template #default>
                <div id="article-title-input" class="flex bg-white w-full">
                  <el-input ref="inputArticleTitle" v-model="currentArticle.title" autosize type="textarea" class="input-title" placeholder="无标题" />
                </div>
              </template>
            </el-skeleton>
            <div class="w-full flex-1 flex justify-center mt-[9px]">
              <el-skeleton style="width: 812px" :loading="isloading" animated>
                <template #template>
                  <el-skeleton-item variant="p" style="width: 723px; height: 22px; margin-top: 16px;" />
                  <el-skeleton-item variant="p" style="width: 638px; height: 22px; margin-top: 16px;" />
                  <el-skeleton-item variant="p" style="width: 569px; height: 22px; margin-top: 16px;" />
                  <el-skeleton-item variant="p" style="width: 666px; height: 22px; margin-top: 16px;" />
                  <el-skeleton-item variant="p" style="width: 723px; height: 22px; margin-top: 16px;" />
                  <el-skeleton-item variant="p" style="width: 466px; height: 22px; margin-top: 16px;" />
                </template>
                <template #default>
                  <div class="h-full w-full relative" @click="editor?.chain().focus().run()">
                    <EditorContent :editor="editor" />
                    <ImageResizer v-if="editor?.isActive('image')" :editor="editor" />
                    <EditorBubbleMenu v-if="editor" :current-article="currentArticle" :editor="editor" @change="handleEditorBubbleMenuChange" />
                    <DocQuote v-if="editor" />
                  </div>
                </template>
              </el-skeleton>
            </div>
          </div>
        </div>
        <div v-if="visibleGuideBoard" class="absolute bottom-0 w-full h-[48%] z-10">
          <DocGuideBoard @change="handleCurrentAi" />
        </div>
      </div>
      <div v-if="!visibleRightSideBar && isMiniEditorWindow" class="h-full w-[470px] basis-[470px]" />
      <div
        v-show="visibleRightSideBar"
        class="h-full overflow-y-auto overflow-x-hidden shrink-0 flex flex-col relative w-[470px] basis-[470px] right-box"
        :class="{
          'px-[16px]': !!currentAI && (currentAI !== 'generate'),
        }"
      >
        <template v-if="editor">
          <DocContinueWriteAsync
            v-if="currentAI === 'continue' || currentAI === 'continue_profession'"
            ref="currentWritingCom"
            :type="currentAI"
            :editor="editor"
            @closed="handleAiClose"
            @change="handleCurrentAi"
          />
          <DocExpandWriteAsync
            v-else-if="currentAI === 'expand'"
            ref="currentWritingCom"
            :editor="editor"
            @closed="handleAiClose"
          />
          <DocPolishWriteOldAsync
            v-else-if="currentAI === 'polish'"
            ref="currentWritingCom"
            :editor="editor"
            @closed="handleAiClose"
          />
          <DocAiWriting
            v-else-if="currentAI === 'generate'"
            ref="currentWritingCom"
            :editor="editor"
            :scroll-container="scrollcontainer"
            @hide="handleAiHide"
            @show="handleAiShow"
            @closed="handleAiClose"
          />
          <DocTitleAsync
            v-else-if="currentAI === 'title'"
            ref="currentWritingCom"
            :editor="editor"
            :input-title="inputArticleTitle"
            @closed="handleAiClose"
          />
        </template>
      </div>
    </div>
    <DocQuoteWindow v-if="editor" :scrollcontainer="scrollcontainer" :visible-right-side-bar="visibleRightSideBar" :editor="editor" />
  </div>
</template>

<style lang="scss" scoped>
.input-title {
  &:deep( textarea) {
    border: none;
    outline: none;
    background: none;
    font-size: 21px;
    font-style: normal;
    font-weight: 700;
    line-height: 1.4em;
    color: black;
    box-shadow: none !important;
    border-radius: 0;
    padding: 0;

    &::placeholder {
      color: rgba(0,0,0,0.36);
    }
  }
}

.right-box {
  border-left: 1px solid rgba(0,0,0,0.10);
}

#article-title-input {
  :deep(textarea) {
    resize: none !important;
    overflow-y: hidden !important;
  }
}
.aigenerte{
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.scrollcontainer::-webkit-scrollbar {
  width: 0px;
}
</style>
