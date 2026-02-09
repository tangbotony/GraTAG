import type { Editor } from '@tiptap/vue-3'
import copy from 'copy-to-clipboard'
import type { Quote, QuoteRes } from '~/composables/api/ai'
import stats from '~/lib/stats'

export interface ProContinueDataType {
  pro_setting_continue_direction: Record<string, string>
  pro_setting_special_request: string
  pro_setting_language_type: string
  pro_setting_length: string
}

export function useWriting(type: ComputedRef<string>, editor: Editor, writeStyle?: Ref<string>) {
  const isEmpty = computed(() => {
    return editor.state.selection.empty
  })

  const data = ref<string[]>([])
  const dataTranformed = ref<string[]>([])
  const dataQuote = ref<Quote[][]>([])
  const route = useRoute()

  const currentText = ref('')
  const currentBeforeText = ref('')
  const currentAfterText = ref('')
  const currentSelection = reactive({
    from: 0,
    to: 0,
  })

  const proContinueData = reactive<ProContinueDataType>({
    pro_setting_continue_direction: {},
    pro_setting_special_request: '',
    pro_setting_language_type: '',
    pro_setting_length: '',
  })

  // tracking
  const requestCount = ref(0)
  const hasRefresh = ref(false)
  const isApplyTracking = ref(false)

  const isInit = ref(false)
  const isValidInput = computed(() => {
    if (type.value === 'title') {
      if (currentArticle.plainText.trim().length > 128 && currentArticle.plainText.trim().length < 3000)
        return true
      else
        return false
    }

    if (type.value === 'polish') {
      if (currentText.value.trim().length > 15 && currentText.value.trim().length <= 10000)
        return true
      else
        return false
    }

    if (currentText.value.trim().length === 0)
      return false
    if (currentText.value.trim().length < 15)
      return false
    if (currentText.value.trim().length > 1000)
      return false
    return true
  })

  const hintText = computed(() => {
    if (type.value === 'title')
      return '正文内容超过128个字, 小于3000字才可自动生成标题哦～'

    if (currentText.value.trim().length === 0) {
      if (type.value === 'continue')
        return '请在页面上输入您想续写的文字，然后选中，再点击随之出现的续写按钮，即可开始续写'

      if (type.value === 'continue_profession')
        return '请在页面上输入您想续写的文字，然后选中，再点击随之出现的续写按钮，即可开始续写'

      if (type.value === 'expand')
        return '请在页面上输入您想扩写的文字，然后选中，再点击随之出现的扩写按钮，即可开始扩写'

      if (type.value === 'polish')
        return '请在页面上输入您想润色的文字，然后选中，再点击随之出现的润色按钮，即可开始润色'

      return ''
    }

    if (currentText.value.length < 15)
      return '选中文字过短'
    if (currentText.value.length > 1000)
      return '选中文字过长'
    return ''
  })

  function getTexts() {
    if (isEmpty.value) {
      isInit.value = true
      return
    }

    const selection = editor.state.selection
    const { text, beforeText, afterText } = getSelectionContext(editor)
    currentText.value = text
    currentBeforeText.value = beforeText
    currentAfterText.value = afterText
    currentSelection.from = selection.from
    currentSelection.to = selection.to
    selectByFromTo(editor, selection.from, selection.to)
    isInit.value = true
  }

  const isloading = ref(false)
  const controller = ref<AbortController | undefined>()
  const timoutFunc = seTimeoutFunc(1000 * 60 * 5)
  async function getData(refresh = false) {
    const id = route.params.id
    if (isloading.value || !id || !isValidInput.value) {
      if (isloading.value)
        ElMessage.warning('生成中暂不支持换一批')

      return
    }
    controller.value?.abort?.()
    controller.value = new AbortController()
    let timeoutId: undefined | number
    const type_ = type.value

    let promise

    if (type_ === 'continue' && !currentArticle.isQuote) {
      promise = useAiContinueWriting({
        selected_content: currentText.value,
        context_above: currentBeforeText.value,
        context_below: currentAfterText.value,
        doc_id: id as string,
        page_title: currentArticle.title,
      }, {
        signal: controller.value.signal,
      })
    }
    else if (type_ === 'continue' && currentArticle.isQuote) {
      promise = useAiContinueWritingQuote({
        selected_content: currentText.value,
        context_above: currentBeforeText.value,
        context_below: currentAfterText.value,
        doc_id: id as string,
        page_title: currentArticle.title,
      }, {
        signal: controller.value.signal,
      })

      timeoutId = timoutFunc(controller.value)
    }
    else if (type_ === 'continue_profession' && currentArticle.isQuote) {
      promise = useAiProContinueWritingQuote({
        selected_content: currentText.value,
        context_above: currentBeforeText.value,
        context_below: currentAfterText.value,
        doc_id: id as string,
        page_title: currentArticle.title,
        ...toRaw(proContinueData),
      }, {
        signal: controller.value.signal,
      })
      timeoutId = timoutFunc(controller.value)
    }
    else if (type_ === 'continue_profession' && !currentArticle.isQuote) {
      promise = useAiProContinueWriting({
        selected_content: currentText.value,
        context_above: currentBeforeText.value,
        context_below: currentAfterText.value,
        doc_id: id as string,
        page_title: currentArticle.title,
        ...toRaw(proContinueData),
      }, {
        signal: controller.value.signal,
      })
    }
    else if (type_ === 'expand') {
      promise = useAiExpandWriting({
        selected_content: currentText.value,
        context_above: currentBeforeText.value,
        context_below: currentAfterText.value,
        doc_id: id as string,
        page_title: currentArticle.title,
      }, {
        signal: controller.value.signal,
      })
    }
    else if (type_ === 'polish') {
      promise = useAiPolishWriting({
        selected_content: currentText.value,
        context_above: currentBeforeText.value,
        context_below: currentAfterText.value,
        polish_type: 'xinhua_style',
        doc_id: id as string,
        page_title: currentArticle.title,
        style: writeStyle!.value,
      }, {
        signal: controller.value.signal,
      })
    }
    else if (type_ === 'title') {
      promise = useAiTitle({
        selected_content: currentArticle.plainText,
        doc_id: id as string,
        style: writeStyle!.value,
      }, {
        signal: controller.value.signal,
      })
    }
    else {
      return
    }

    isloading.value = true
    const { data: result, error } = await promise
    isloading.value = false
    clearTimeout(timeoutId)
    controller.value = undefined

    if (!result.value?.result)
      return

    if (error.value)
      return

    if (refresh) {
      data.value = []
      dataTranformed.value = []
    }

    let resultForData: string[] = []

    const isQuote = (type_ === 'continue' && currentArticle.isQuote) || (type_ === 'continue_profession' && currentArticle.isQuote)

    if (isQuote)
      resultForData = (result.value.result as QuoteRes[]).map((item: QuoteRes) => item.write_text)
    else
      resultForData = (result.value.result as string[]) || []

    let resultForDataTranformed: string[] = []
    let resultForQuotes: Quote[][] = []
    if (isQuote) {
      resultForDataTranformed = (result.value.result as QuoteRes[]).map((item: QuoteRes) => {
        let text = item.write_text
        text = splitText(text, type_)
        text = transformQuoteData(text, item)
        return text
      })

      resultForQuotes = (result.value.result as QuoteRes[]).map((item: QuoteRes) => {
        return extraQuote(item)
      })
      collectRefContent(resultForQuotes)
    }
    else {
      resultForDataTranformed = (result.value.result as string[]).map((item: string) => {
        return splitText(item, type_)
      })
    }

    resultForData = resultForData.map(i => fullAngle2halfAngle(i))
    resultForDataTranformed = resultForDataTranformed.map(i => fullAngle2halfAngle(i))
    if (refresh || data.value.length === 0) {
      data.value = resultForData
      dataTranformed.value = resultForDataTranformed
      dataQuote.value = resultForQuotes
    }
    else {
      data.value = [...data.value, ...resultForData]
      dataTranformed.value = [...dataTranformed.value, ...resultForDataTranformed]
      dataQuote.value = [...dataQuote.value, ...resultForQuotes]
    }

    stats.track(`text-${type_}`, {
      action: 'generate',
      value: data.value.length,
    })

    if (refresh)
      hasRefresh.value = true

    requestCount.value += 1
    if (requestCount.value === 1) {
      stats.track(`text-${type_}`, {
        action: 'request_input',
      })
    }
  }

  function handleCopy(event: Event, index: number) {
    event.stopPropagation()
    if (dataTranformed.value[index]) {
      const plain_text = data.value[index]

      copy(plain_text, {
        format: 'text/html',
        onCopy(data: any) {
          data.setData('text/plain', plain_text)
        },
      })

      ElMessage({
        message: '复制成功',
        type: 'success',
      })
    }
  }

  // ---
  const selectedTextIndex = ref(0)

  const isApply = ref(false)
  const isApplyIndexs = ref<number[]>([])

  const lastApplyFrom = ref<number | null>(null)
  const lastApplyTo = ref<number | null>(null)
  const lastApplyText = ref<string | null>(null)

  function clearState(isSelectOrigin = true) {
    const currentSelection_ = editor.state.selection
    let isDiff = false
    if (catchTextBetweenError(editor, currentSelection_.from, currentSelection_.to) !== lastApplyText.value)
      isDiff = true

    clearText()
    selectedTextIndex.value = 0
    lastApplyFrom.value = null
    lastApplyTo.value = null
    lastApplyText.value = null
    isApply.value = false
    isApplyIndexs.value = []
    data.value = []
    dataTranformed.value = []
    isloading.value = false
    controller.value?.abort?.()

    if (isSelectOrigin
      && currentText.value && currentText.value === catchTextBetweenError(editor, currentSelection.from, currentSelection.to)
      && !isDiff
    )
      selectByFromTo(editor, currentSelection.from, currentSelection.to)

    currentText.value = ''
    currentBeforeText.value = ''
    currentAfterText.value = ''
    currentSelection.from = 0
    currentSelection.to = 0

    requestCount.value = 0
    hasRefresh.value = false
    isApplyTracking.value = false
    isInit.value = false
  }

  function clearText() {
    if (!['continue', 'continue_profession'].includes(type.value))
      return

    if (isApply.value)
      return
    if (lastApplyFrom.value === null || lastApplyTo.value === null || lastApplyText.value === null)
      return

    clearSpecifiedText(editor, lastApplyFrom.value, lastApplyTo.value, lastApplyText.value)
  }

  function activeCurrentSelection() {
    const currentSelection = editor.state.selection
    editor.chain().focus().setTextSelection(currentSelection).run()
  }

  function replaceText(index: number, from: number, to?: number) {
    const text = dataTranformed.value[index] as string
    editor.chain().focus().insertContentAt(to
      ? {
          from,
          to,
        }
      : from, text, {
      updateSelection: true,
    }).run()

    selectByFromTo(editor, from, editor.state.selection.to)

    const afterSelection = editor.state.selection
    lastApplyFrom.value = afterSelection.from
    lastApplyTo.value = afterSelection.to
    lastApplyText.value = catchTextBetweenError(editor, afterSelection.from, afterSelection.to)
  }

  function trackForAppy(index: number) {
    // tracking
    if (!hasRefresh.value && index <= 2 && !isApplyTracking.value) {
      stats.track(`text-${type.value}`, {
        action: 'apply_3',
      })
      isApplyTracking.value = true
    }
  }

  const isRefreh = ref(false)

  return {
    handleCopy,
    getTexts,
    getData,
    isInit,
    isEmpty,
    isloading,
    data,
    currentSelection,
    currentText,
    currentBeforeText,
    currentAfterText,

    selectedTextIndex,
    isApply,
    isApplyIndexs,
    lastApplyFrom,
    lastApplyTo,
    lastApplyText,
    clearState,
    clearText,
    activeCurrentSelection,
    replaceText,

    proContinueData,
    dataTranformed,
    dataQuote,
    requestCount,
    hasRefresh,
    isApplyTracking,
    trackForAppy,
    isValidInput,
    hintText,
    controller,
    isRefreh,
    currentArticle,
  }
}

export function collectRefContent(data: Quote[][]) {
  data.forEach((item) => {
    item.forEach((quote) => {
      currentArticle.referenceContent.set(quote.url, quote.content)

      if (currentArticle.referenceDescs.has(quote.url)) {
        const descs = currentArticle.referenceDescs.get(quote.url) as string[]
        descs.push(quote.description)
        currentArticle.referenceDescs.set(quote.url, descs)
      }
      else {
        currentArticle.referenceDescs.set(quote.url, [quote.description])
      }
    })
  })
}

export function splitText(text: string, type: string) {
  const isContinue = type.startsWith('continue')

  const texts = text.split('\n')

  // 开头两个空格, 或有多个段落
  const isParagraphs = texts.length > 1
  const firstTextIsParagraph = (text.slice(0, 2).trim().length === 0)

  if (isContinue && firstTextIsParagraph)
    text = `<p>\t${texts[0]}</p>`
  else if (!isContinue && isParagraphs)
    text = `\t${texts[0]}`
  else if (isParagraphs)
    text = `<p>\t${texts[0]}</p>`
  else
    text = `${texts[0]}`

  if (isParagraphs) {
    text += texts.slice(1).map((i) => {
      return `<p>\t${i}</p>`
    }).join('')
  }
  return text
}

function transformQuoteData(all_text: string, currentQuote: QuoteRes) {
  let text = all_text
  const dic = currentQuote.ref_item
  const dicKeies = Object.keys(dic)

  // 排序
  const indexsSortMap = new Map()
  dicKeies.forEach((key) => {
    indexsSortMap.set(key, all_text.indexOf(key))
  })
  dicKeies.sort((a, b) => {
    return indexsSortMap.get(a) - indexsSortMap.get(b)
  })

  // 同处引用去重
  const indexPositionMap = new Map<number, string[]>()
  let postionText = text
  dicKeies.forEach((key) => {
    const position = postionText.indexOf(key)
    if (position === -1)
      return

    if (indexPositionMap.has(position)) {
      const keys = indexPositionMap.get(position) as string[]
      keys.push(key)
      indexPositionMap.set(position, keys)
    }
    else {
      indexPositionMap.set(position, [key])
    }
    postionText = postionText.replace(key, '')
  })

  const queue: (Quote & { key: string; index: number; pos: number })[] = []
  // 多余的key
  const spareKeys: string[] = []
  indexPositionMap.forEach((keys, pos) => {
    const map = new Map<string, any>()
    keys.forEach((key) => {
      let desc = dic[key].description
      desc = desc.trim()
      let startOrEnd = true
      const content = currentQuote.ref_item[key].content
      while (!content.includes(desc)) {
        if (startOrEnd) {
          desc = desc.slice(1)
          desc = desc.trim()
          startOrEnd = false
        }
        else {
          desc = desc.slice(0, -1)
          desc = desc.trim()
          startOrEnd = true
        }
      }
      dic[key].description = desc

      if (desc.length === 0)
        return

      if (map.has(dic[key].url)) {
        const item = map.get(dic[key].url)
        item.description += `|||${dic[key].description}`
        spareKeys.push(key)
      }
      else {
        const item = structuredClone(toRaw(dic[key])) as (Quote & { key: string; index: number; pos: number })
        item.key = key
        item.index = 1
        item.pos = pos
        map.set(dic[key].url, item)
        queue.push(item)
      }
    })
  })

  // 删除多余key
  spareKeys.forEach((key) => {
    text = text.replaceAll(key, '')
  })

  // 生成span
  const groupMap = new Map<number, (Quote & { key: string; index: number; pos: number })[]>()
  const indexUrlMap = new Map()
  let indexCount = 1
  queue.forEach((item) => {
    let index
    if (indexUrlMap.has(item.url)) {
      index = indexUrlMap.get(item.url) as number
    }
    else {
      index = indexCount
      indexUrlMap.set(item.url, indexCount)
      indexCount += 1
    }

    item.index = index
    if (groupMap.has(item.pos)) {
      const keys = groupMap.get(item.pos)!
      keys.push(item)
      groupMap.set(item.pos, keys)
    }
    else {
      groupMap.set(item.pos, [item])
    }
  })

  // 保证同一处的引证按顺序排列
  groupMap.forEach((keys) => {
    if (keys.length > 1) {
      const keysStr = keys.map(item => item.key).join('')
      keys.sort((a, b) => {
        return (a.index - b.index)
      })
      const keysStr_ = keys.map(item => item.key).join('')
      if (keysStr !== keysStr_)
        text = text.replace(keysStr, keysStr_)
    }
  })
  queue.forEach((item) => {
    text = text.replaceAll(item.key, `<span data-type="quote" data-title="${item.title}" data-href="${item.url}" data-description="${item.description}" >${item.index}</span>`)
  })
  return text
}

interface QuoteMates {
  [key: string]: QuoteMatObj
}

interface QuoteMatObj {
  ext: string
  material_id: string
  material_name: string
  raw_file_path: string
}

export function transformQuoteSumData(all_text: string, currentQuote: Quote3, materials: QuoteMates) {
  let text = all_text
  const dic = currentQuote.ref_item
  const dicKeies = Object.keys(dic)

  // 排序
  const indexsSortMap = new Map()
  dicKeies.forEach((key) => {
    indexsSortMap.set(key, all_text.indexOf(key))
  })
  dicKeies.sort((a, b) => {
    return indexsSortMap.get(a) - indexsSortMap.get(b)
  })

  // 同处引用去重
  const indexPositionMap = new Map<number, string[]>()
  let postionText = text
  dicKeies.forEach((key) => {
    const position = postionText.indexOf(key)
    if (position === -1)
      return

    if (indexPositionMap.has(position)) {
      const keys = indexPositionMap.get(position) as string[]
      keys.push(key)
      indexPositionMap.set(position, keys)
    }
    else {
      indexPositionMap.set(position, [key])
    }
    postionText = postionText.replace(key, '')
  })

  const queue: (Quote & { key: string; index: number; pos: number; source_id: string })[] = []
  // 多余的key
  const spareKeys: string[] = []
  indexPositionMap.forEach((keys, pos) => {
    const map = new Map<string, any>()
    keys.forEach((key) => {
      let desc = dic[key].description
      desc = desc.trim()
      let startOrEnd = true
      const content = currentQuote.ref_item[key].description
      while (!content.includes(desc)) {
        if (startOrEnd) {
          desc = desc.slice(1)
          desc = desc.trim()
          startOrEnd = false
        }
        else {
          desc = desc.slice(0, -1)
          desc = desc.trim()
          startOrEnd = true
        }
      }
      dic[key].description = desc

      if (desc.length === 0)
        return

      if (map.has(dic[key].url)) {
        const item = map.get(dic[key].url)
        item.description += `|||${dic[key].description}`
        spareKeys.push(key)
      }
      else {
        const item = structuredClone(toRaw(dic[key])) as (Quote & { key: string; index: number; pos: number; source_id: string })
        item.key = key
        item.index = 1
        item.pos = pos
        map.set(dic[key].url, item)
        queue.push(item)
      }
    })
  })

  // 删除多余key
  spareKeys.forEach((key) => {
    text = text.replaceAll(key, '')
  })

  // 生成span
  const groupMap = new Map<number, (Quote & { key: string; index: number; pos: number })[]>()
  const indexUrlMap = new Map()
  let indexCount = 1
  queue.forEach((item) => {
    let index
    if (indexUrlMap.has(item.url)) {
      index = indexUrlMap.get(item.url) as number
    }
    else {
      index = indexCount
      indexUrlMap.set(item.url, indexCount)
      indexCount += 1
    }

    item.index = index
    if (groupMap.has(item.pos)) {
      const keys = groupMap.get(item.pos)!
      keys.push(item)
      groupMap.set(item.pos, keys)
    }
    else {
      groupMap.set(item.pos, [item])
    }
  })

  // 保证同一处的引证按顺序排列
  groupMap.forEach((keys) => {
    if (keys.length > 1) {
      const keysStr = keys.map(item => item.key).join('')
      keys.sort((a, b) => {
        return (a.index - b.index)
      })
      const keysStr_ = keys.map(item => item.key).join('')
      if (keysStr !== keysStr_)
        text = text.replace(keysStr, keysStr_)
    }
  })
  queue.forEach((item) => {
    if (item.source_id && materials[item.source_id])
      text = text.replaceAll(item.key, `<span data-type="quote" data-title="${materials[item.source_id].material_name}" data-href="sourceid:${item.source_id}&ext:${materials[item.source_id].ext}" data-description="${item.description}" >${item.index}</span>`)
    else
      text = text.replaceAll(item.key, `<span data-type="quote" data-title="${item.title}" data-href="${item.url}" data-description="${item.description}" >${item.index}</span>`)
  })
  return text
}

export function extraQuote(currentQuote: QuoteRes) {
  const text = currentQuote.write_text
  const dic = currentQuote.ref_item
  const dicKeies = Object.keys(dic)
  const indexsSortMap = new Map()

  dicKeies.forEach((key) => {
    indexsSortMap.set(key, text.indexOf(key))
  })

  dicKeies.sort((a, b) => {
    return indexsSortMap.get(a) - indexsSortMap.get(b)
  })

  const all_quotes: Quote[] = []
  const indexUrlMap = new Map()
  dicKeies.forEach((key) => {
    if (!indexUrlMap.has(dic[key].url)) {
      indexUrlMap.set(dic[key].url, dic[key])
      all_quotes.push(dic[key])
    }
  })

  return all_quotes
}

function seTimeoutFunc(time = 1000) {
  let timeoutId: undefined | number
  return (controller: AbortController) => {
    if (timeoutId)
      clearTimeout(timeoutId)

    timeoutId = window.setTimeout(() => {
      controller?.abort?.()
      ElMessage.warning('亲，当前服务并发请求较高，请稍后再尝试请求～')
    }, time)
    return timeoutId
  }
}
