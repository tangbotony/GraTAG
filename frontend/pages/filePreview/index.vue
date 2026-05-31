<script setup lang="ts">
import { useRoute } from 'vue-router'
import Token from '~/lib/token'

definePageMeta({
  keepalive: false,
  key: 'file-preview',
})
const route = useRoute()

const baseURL = import.meta.env.VITE_API
const isEnv = import.meta.env.VITE_ENV === 'sit'
const token = new Token(isEnv ? 'dev' : 'prod')

const iframeContainerRef = ref()
let _iframeWindow: Window | null = null
let _iframe: HTMLIFrameElement | null = null

function setOptions() {
  if (!_iframeWindow)
    return
  _iframeWindow.PDFViewerApplicationOptions.set('isEvalSupported', false)
  _iframeWindow.PDFViewerApplicationOptions.set('defaultUrl', '')
  _iframeWindow.PDFViewerApplicationOptions.set('historyUpdateUrl', false)
  _iframeWindow.PDFViewerApplicationOptions.set('textLayerMode', 1)
  _iframeWindow.PDFViewerApplicationOptions.set('sidebarViewOnLoad', 0)
  _iframeWindow.PDFViewerApplicationOptions.set('ignoreDestinationZoom', true)
  _iframeWindow.PDFViewerApplicationOptions.set('renderInteractiveForms', false)
  _iframeWindow.PDFViewerApplicationOptions.set('printResolution', 300)
}

const currentPdfUrl = computed(() => {
  if (!route.query.pdfid || route.query.fileext === 'txt')
    return ''
  if (route.query.version !== 'v2')
    return `${baseURL}/api/material/preview/${route.query.pdfid}?to_pdf=true`

  else
    return `${baseURL}/api/doc_search/${route.query.pdfid}`
})

async function initPdf() {
  _iframeWindow = null
  _iframe = null

  window.addEventListener('webviewerloaded', () => {
    _iframeWindow = _iframe!.contentWindow
    setOptions()
  })

  try {
    _iframe = document.createElement('iframe')
    _iframe.setAttribute('style', 'width: 100%; height: 100%; border: none;')
    _iframe.src = '/pdf/web/viewer.html'
    _iframe.addEventListener('load', async () => {
      _iframeWindow!.PDFViewerApplication.close()
      if (route.query.version !== 'v2') {
        _iframeWindow!.PDFViewerApplication.open({
          url: currentPdfUrl.value,
          httpHeaders: { Authorization: `Bearer ${token.token}` },
        })
      }
      else {
        _iframeWindow!.PDFViewerApplication.open({
          url: currentPdfUrl.value,
          httpHeaders: { Authorization: `Bearer ${token.token}` },
        })
      }
      window.PDFViewerApplication = _iframeWindow!.PDFViewerApplication
      window.if = _iframeWindow!
    })
    iframeContainerRef.value.appendChild(_iframe)
  }
  catch (error) {
    console.error(error)
  }
}

const textData = ref('')
async function initTxt() {
  let txtdata: any = ''
  if (route.query.version !== 'v2')
    txtdata = await materialArticle(route.query.pdfid)

  else
    txtdata = await useGetDocSearch(route.query.pdfid as string, 'txt')

  textData.value = txtdata.data.value
}

onMounted(() => {
  if (route.query.fileext !== 'txt')
    initPdf()
  else
    initTxt()
})
onBeforeUnmount(() => {
  _iframeWindow?.PDFViewerApplication.close()
  if (_iframe)
    iframeContainerRef.value.removeChild(_iframe)
})

async function download() {
  try {
    const response = await fetch(currentPdfUrl.value, {
      headers: {
        Authorization: `Bearer ${token.token}`,
      },
    })
    if (!response.ok)
      throw new Error(`HTTP error! status: ${response.status}`)

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    useFileDownload(url, `${route.query.pdfid}.pdf`)
  }
  catch (error) {
    console.error(error)
  }
}
</script>

<template>
  <div
    ref="iframeContainerRef" class="w-full h-full" :class="{
      'overflow-y-auto': route.query.fileext === 'txt',
    }"
  >
    <div v-if="route.query.fileext === 'txt'" class="p-4 whitespace-pre-wrap" v-html="textData" />
  </div>
  <div v-if="route.query.fileext !== 'txt'" class="fixed top-[5px] right-[18px]">
    <el-button @click="download">
      下载
    </el-button>
  </div>
</template>
