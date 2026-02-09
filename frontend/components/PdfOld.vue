<script setup lang="ts">
import Token from '~/lib/token'

const props = defineProps<{
  url: string
  currentdesc: string
}>()
const { currentdesc, url } = toRefs(props)
const isEnv = import.meta.env.VITE_ENV === 'sit'
const token = new Token(isEnv ? 'dev' : 'prod')

const iframeContainerRef = ref()

let _iframeWindow: Window | null = null
let _iframe: HTMLIFrameElement | null = null

let findTimeoutId: null | NodeJS.Timeout = null
let hasReFind = false

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

window.addEventListener('webviewerloaded', () => {
  _iframeWindow = _iframe!.contentWindow
  setOptions()
})

const isloading = ref(false)

onMounted(async () => {
  try {
    // isloading.value = true
    // const data = await fetch(`${baseURL}/api/material/preview/${pdfid.value}?to_pdf`, {
    //   headers: {
    //     Authorization: `Bearer ${token.token}`,
    //   },
    // })
    // const buffer = await data.arrayBuffer()
    // isloading.value = false

    _iframe = document.createElement('iframe')
    _iframe.setAttribute('style', 'width: 100%; height: 100%; border: none;')
    _iframe.src = '/pdf/web/viewer.html'
    _iframe.addEventListener('load', async () => {
      _iframeWindow!.PDFViewerApplication.close()
      _iframeWindow!.PDFViewerApplication.open({
        url: url.value,
        httpHeaders: { Authorization: `Bearer ${token.token}` },
        // data: buffer,
      })
      window.PDFViewerApplication = _iframeWindow!.PDFViewerApplication
      window.if = _iframeWindow!

      await new Promise(resolve => setTimeout(resolve, 100))
      _iframeWindow!.PDFViewerApplication.eventBus.on('documentinit', () => {
        _iframeWindow!.PDFViewerApplication.pdfViewer.currentScaleValue = 1
        hasReFind = false
        find(currentdesc.value)
      })

      _iframeWindow!.PDFViewerApplication.eventBus.on('updatefindmatchescount', (state: any) => {
        if (state.matchesCount.total !== 0) {
          if (findTimeoutId) {
            clearTimeout(findTimeoutId)
            findTimeoutId = null
          }
        }
        scrollInto()
      })

      _iframeWindow!.PDFViewerApplication.eventBus.on('updatefindcontrolstate', (state: any) => {
        if (state.state !== 3 && !hasReFind) {
          hasReFind = true
          setTimeoutFind()
        }
      })
    })
    iframeContainerRef.value.appendChild(_iframe)
  }
  catch (e) {
    console.error(e)
  }
  finally {
    // isloading.value = false
  }
})

async function scrollInto() {
  if (!_iframeWindow)
    return
  await new Promise(resolve => setTimeout(resolve, 200))
  const doms = _iframeWindow.document.querySelectorAll('.highlight.selected')
  if (doms.length === 0)
    return
  let maxLengthDom = doms[0]
  let maxLength = 0
  doms.forEach((dom: any) => {
    if (dom.textContent.length > maxLength) {
      maxLength = dom.textContent.length
      maxLengthDom = dom
    }
  })
  maxLengthDom?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' })
}

function findFragment() {
  const words = currentdesc.value.split(/[\t\n \uFFFD]+/).filter(i => !!i && i.length > 2)
  const query = words[0]
  find(query)
}

function setTimeoutFind() {
  if (findTimeoutId)
    clearTimeout(findTimeoutId)
  findTimeoutId = setTimeout(() => {
    if (!_iframeWindow)
      return
    const doms = _iframeWindow.document.querySelectorAll('.highlight.selected')
    if (doms.length === 0)
      findFragment()
  }, 200)
}

async function find(value: string) {
  if (!value || value.trim() === '' || !_iframeWindow)
    return
  const findState = {
    active: true,
    caseSensitive: false,
    entireWord: false,
    highlightAll: true,
    popupOpen: true,
    query: value,
    result: null,
  }

  window.PDFViewerApplication?.eventBus.dispatch('find', {
    source: _iframeWindow,
    type: 'find',
    query: findState.query,
    phraseSearch: true,
    caseSensitive: findState.caseSensitive,
    entireWord: findState.entireWord,
    highlightAll: findState.highlightAll,
    findPrevious: undefined,
  })
}

watch(url, async () => {
  if (_iframeWindow) {
    hasReFind = false
    _iframeWindow.PDFViewerApplication.close()
    try {
      // isloading.value = true
      // const data = await fetch(`${baseURL}/api/material/preview/${pdfid.value}?to_pdf`, {
      //   headers: {
      //     Authorization: `Bearer ${token.token}`,
      //   },
      // })
      // const buffer = await data.arrayBuffer()
      // isloading.value = false
      _iframeWindow.PDFViewerApplication.open({
        url: url.value,
        httpHeaders: { Authorization: `Bearer ${token.token}` },
        // data: buffer,
      })
    }
    catch (e) {
      console.error(e)
    }
    finally {
      // isloading.value = false
    }
  }
})

watch(currentdesc, (value) => {
  hasReFind = false
  find(value)
})

onBeforeUnmount(() => {
  _iframeWindow?.PDFViewerApplication.close()
  iframeContainerRef.value.removeChild(_iframe!)
})
</script>

<template>
  <div ref="iframeContainerRef" class="w-full h-full relative flex items-center justify-center">
    <img
      v-if="isloading"
      class="absolute left-50% top-50% transform -translate-x-1/2 -translate-y-1/2 z-100"
      :style="{
        width: '40px',
      }" src="~/assets/images/generate/generate-loading.png"
    >
  </div>
</template>

<style lang="scss" scoped>
</style>
