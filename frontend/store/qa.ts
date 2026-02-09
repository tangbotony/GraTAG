import type { QaAdditionQuery, QaPairInfo, RefDoc } from '~/composables/api/qa'

export enum QaAnswerType {
  First = 'first',
  Append = 'append',
  ReGenerate = 're_generate',
  Subscription = 'subscription',
  DeleteRef = 'delete_ref',
  Recommend = 'recommend',
}

export enum QaProgressState {
  Analyze = 'analyze',
  Supplement = 'supplement',
  Search = 'search',
  Organize = 'organize',
  Complete = 'complete',
  TextEnd = 'text_end',
  Finish = 'finish',
}

export enum QaMode {
  WEB = 'web',
  DOC = 'doc',
}

type SearchModeType = 'pro' | 'lite' | 'doc'

export interface QaCollectionState {
  progress: QaProgressState
  id: string
  query: string
  pairs: QaPair[]
  is_subscribed: boolean
  controller?: AbortController
  curPairId?: string
  curType?: QaAnswerType
  curAdditional?: QaAdditionQuery
  curDeleteNews: string[]
  create_time?: string
  pairsIds: string[]
  curTimelineSort: boolean
  currentSearchMode: SearchModeType
}

const useQaStore = defineStore('qa', () => {
  const qaState = reactive<{
    seriesId: string
    firstQuery: string
    collection: QaCollectionState[]
    mode: string
    docIds?: string[]
    docs: QaDoc[]
  }>({
    seriesId: '',
    firstQuery: '',
    mode: '',
    collection: [],
    docIds: undefined,
    docs: [],
  })

  const isPro = computed(() => {
    return !!currentUser.value?.extend_data?.is_qa_pro
  })

  const qaSearchMode = computed<SearchModeType>(() => {
    if (qaState.mode === QaMode.WEB && isPro.value)
      return 'pro'
    else if (qaState.mode === QaMode.WEB && !isPro.value)
      return 'lite'
    else
      return 'doc'
  })

  const scrollerContainer = ref<HTMLElement | null>(null)

  const scrollProgress = ref(0)

  const router = useRouter()
  const illegalCodeEnd = /\[[a-zA-Z0-9]+\]$/

  const replaceTimeRef = (timeline: QaTimeline, qaInfo: QaPairInfo, collection_id: string) => {
    timeline.events.forEach((event, index) => {
      if (event.index === undefined)
        event.index = index
    })

    timeline.events.forEach((event) => {
      event.event_list.forEach((item) => {
        Object.keys(item.reference_object).forEach((key) => {
          const ref = item.reference_object[key]
          const i = qaInfo.ref_pages_list.find(i => i._id === ref.news_id)
          if (i?.index)
            item.event_abstract_html = item.event_abstract.replace(`${key}`, `<span class="qa-ref" data-type="qa-time-ref" data-id="${key.slice(1, -1)}" data-url="${ref.url}" data-coll-id="${collection_id}"  >${i?.index || ''}</span>`)
        })
      })
    })

    const collection = qaState.collection.find(item => item.id === collection_id)
    timeline.events.sort((a, b) => {
      if (collection?.curTimelineSort)
        return a.index! - b.index!

      return b.index! - a.index!
    })
    timeline.events.forEach((event) => {
      event.event_list.sort((a, b) => {
        const atime = a.start_time
        const btime = b.start_time

        if (atime.startsWith('-') && btime.startsWith('-')) {
          if (collection?.curTimelineSort)
            return atime > btime ? -1 : 1
          return atime > btime ? 1 : -1
        }

        if (collection?.curTimelineSort)
          return atime > btime ? 1 : -1
        return atime > btime ? -1 : 1
      })
    })
  }

  const replaceImgs = (imgs: { id: string; url: string }[], answer: string) => {
    imgs.forEach((img) => {
      answer = answer.replaceAll(`<xinyu type="image" id="${img.id}"/>`, `![image](${img.url})\n`)
    })
    return answer
  }

  const ask = async (qa_pair_collection_id: string) => {
    const collection = qaState.collection.find(item => item.id === qa_pair_collection_id)
    if (!collection || !collection.curPairId || !collection.curType)
      return

    try {
      const controller = new AbortController()
      collection.controller = controller
      const res = await usePostQaAsk({
        qa_series_id: qaState.seriesId,
        qa_pair_collection_id,
        qa_pair_id: collection.curPairId,
        query: collection.query,
        type: collection.curType,
        delete_news_list: collection.curDeleteNews || [],
        additional_query: collection.curAdditional,
        search_mode: collection.currentSearchMode,
      }, controller)
      const pair = collection.pairs.find(i => i._id === collection.curPairId)!

      const queue: string[] = []
      let queueIntervalId: null | NodeJS.Timeout = null
      let images: { id: string; url: string; origin_doc_url: string }[] = []

      for await (const chunk of res) {
        if (typeof chunk === 'string' && chunk === '[DONE]')
          break

        const results = chunk.results
        if (!results?.type)
          continue

        if (results.type === 'state') {
          pair.version = (results as QaAskState).version
          collection.progress = results.data as QaProgressState
        }
        else if (results.type === 'qa_pair_info') {
          const qa_info = (results.data as QaPairInfo)

          qa_info.ref_pages_list = []
          Object.keys(qa_info.ref_pages).forEach((key) => {
            qa_info.ref_pages_list.push(
              qa_info.ref_pages[key],
            )
          })

          if (qaState.mode === QaMode.WEB) {
            // 第二个到的qa_pair_info
            if (pair.general_answer && pair.reference && pair.qa_info?.ref_pages_list && pair.qa_info.ref_pages_list.length > 0)
              calcRefPageIndex(pair.general_answer, pair.reference, qa_info.ref_pages_list, [QaProgressState.TextEnd, QaProgressState.Finish].includes(collection.progress))
          }

          pair.qa_info = qa_info
        }
        else if (results.type === 'text') {
          if (!queueIntervalId) {
            pair.general_answer = ''

            queueIntervalId = setInterval(() => {
              if (queueIntervalId && queue.length === 0 && [QaProgressState.Finish, QaProgressState.TextEnd].includes(collection.progress)) {
                clearInterval(queueIntervalId)
                queueIntervalId = null
                return
              }

              if (images.length > 0) {
                const images_ = images.concat()
                images = []

                images_.forEach((img) => {
                  const index = queue.findIndex(i => i === `<xinyu type="image" id="${img.id}"/>`)
                  if (index !== -1) {
                    const str = `![image](${img.url})\n`
                    queue[index] = str
                  }

                  if (pair.general_answer?.includes(`<xinyu type="image" id="${img.id}"/>`))
                    pair.general_answer = pair.general_answer!.replace(`<xinyu type="image" id="${img.id}"/>`, `![image](${img.url})\n`)
                })
              }

              const data = queue.shift()
              if (data)
                pair.general_answer += data

              if (pair.qa_info && pair.general_answer && pair.reference && illegalCodeEnd.test(pair.general_answer))
                calcRefPageIndexByMode(pair.general_answer, pair.reference, pair.qa_info, false)

              if ([QaProgressState.TextEnd, QaProgressState.Finish].includes(collection.progress) && queue.length === 0) {
                if (pair.qa_info && pair.general_answer && pair.reference)

                  calcRefPageIndexByMode(pair.general_answer, pair.reference, pair.qa_info)

                if (pair.timeline_id?.events && pair.qa_info && collection.id)
                  replaceTimeRef(pair.timeline_id, pair.qa_info, collection.id)
              }
            }, 20)
          }
          if (results.data)
            queue.push(results.data as string)
        }
        else if (results.type === 'ref_answer') {
          pair.reference = (results.data as AnswerRef[])
          pair.reference.forEach((r) => {
            if (r.poly) {
              const datas = r.poly.map((i: string) => i.split(','))
              r.polyDto = datas.map((i) => {
                return { page: Number(i[0]), poly: [Number(i[1]), Number(i[2]), Number(i[3]), Number(i[4])] }
              })
            }
          })
        }
        else if (results.type === 'recommendation') {
          pair.recommend_query = (results.data as string[])
        }
        else if (results.type === 'timeline') {
          pair.timeline_id = (results.data as QaTimeline)
          if (pair.timeline_id?.events && pair.qa_info && collection.id)
            replaceTimeRef(pair.timeline_id, pair.qa_info, collection.id)
        }
        else if (results.type === 'image') {
          const res = results as QaAskImg
          images = images.concat(res.data)
          queue.push('')
          pair.images = res.data
        }
        else if (results.type === 'text_end') {
          collection.progress = QaProgressState.TextEnd
          if (queue.length === 0) {
            if (pair.general_answer && pair.reference && pair.qa_info)
              calcRefPageIndexByMode(pair.general_answer, pair.reference, pair.qa_info)

            if (pair.timeline_id?.events && pair.qa_info && collection.id)
              replaceTimeRef(pair.timeline_id, pair.qa_info, collection.id)
          }
        }
      }
    }
    catch (e) {
      console.error(e)
    }
    finally {
      collection.progress = QaProgressState.Finish
      collection.controller = undefined
    }
  }

  const beforeAsk = (
    qa_pair_collection_id: string, qa_series_id: string, query: string,
    type: QaAnswerType,
  ) => {
    qaState.seriesId = qa_series_id
    qaState.collection.push({
      progress: QaProgressState.Analyze,
      id: qa_pair_collection_id,
      query,
      curType: type,
      is_subscribed: false,
      pairs: [],
      curDeleteNews: [],
      pairsIds: [],
      curTimelineSort: false,
      currentSearchMode: qaSearchMode.value,
    })
  }

  const setFirstQuery = (query: string, mode: string, docIds?: string[]) => {
    qaState.firstQuery = query
    qaState.mode = mode
    if (docIds)
      qaState.docIds = docIds
  }

  const createSeries = async (query: string) => {
    const { data, error } = await usePostQaSeries(query, qaState.docIds)
    if (error.value || !data.value)
      return

    return data.value?.results
  }

  const completeAsk = async (query: string, qa_series_id: string, qa_pair_collection_id: string, type: QaAnswerType) => {
    const collection = qaState.collection.find(item => item.id === qa_pair_collection_id)
    if (!collection)
      return

    const controller = new AbortController()
    collection.controller = controller
    const { data, error } = await usePostQaCompleteAsk({
      qa_series_id,
      qa_pair_collection_id,
      query,
      type,
      search_mode: collection.currentSearchMode,
    }, controller.signal)

    collection.controller = undefined
    collection.curPairId = data.value?.results.qa_pair_id
    const pair = reactive({ _id: collection.curPairId, search_mode: collection.currentSearchMode }) as QaPair
    collection.pairs.unshift(pair)
    if (!collection?.pairsIds)
      collection.pairsIds = []

    collection.pairsIds.unshift(pair._id)

    if (error.value || !data.value) {
      collection.progress = QaProgressState.Finish
      return
    }

    return data.value?.results
  }

  const reset = () => {
    qaState.collection.forEach((coll) => {
      coll.controller?.abort()
    })
    qaState.collection = []
    qaState.firstQuery = ''
    qaState.seriesId = ''
    qaState.mode = ''
    qaState.docIds = undefined
    qaState.docs = []
  }

  const completeOrReject = async (item: QaCollectionState) => {
    const r = await completeAsk(item.query, qaState.seriesId, item.id, item.curType!)
    if (r) {
      const currPair = item.pairs[0]!
      currPair.unsupported = r.unsupported
      if (r.type === 'reject') {
        if (qaState.collection.length === 1 && item.pairs.length === 1)
          router.replace('/search')
        else
          item.progress = QaProgressState.Finish
        await new Promise(resolve => setTimeout(resolve, 200))
        const dom = document.getElementById('search-container') as HTMLElement
        ElMessage({
          type: 'error',
          message: '我在努力进化中，现在还回答不了您这个问题呢~',
          appendTo: dom,
          customClass: '!absolute',
        })
      }
      else if (r.type === 'additional_query') {
        item.curAdditional = r.additional_query
        item.progress = QaProgressState.Supplement
      }
      else {
        item.progress = QaProgressState.Analyze
        ask(item.id)
      }
    }
  }

  const createPair = async (collection: QaCollectionState) => {
    const { data, error } = await useAddQaPair(collection.query, qaState.seriesId, collection.id, collection.currentSearchMode)
    if (error.value || !data.value)
      return

    const qa_pair_id = data.value.results.qa_pair_id

    collection.curPairId = qa_pair_id
    const pair = reactive({ _id: collection.curPairId, search_mode: collection.currentSearchMode }) as QaPair
    collection.pairs.unshift(pair)
    if (!collection?.pairsIds)
      collection.pairsIds = []

    collection.pairsIds.unshift(pair._id)
    collection.progress = QaProgressState.Analyze
    ask(collection.id)
  }

  const createCollection = async (type: QaAnswerType, query: string) => {
    const { data, error } = await usePostQaCollection(qaState.seriesId)
    if (error.value || !data.value)
      return
    const { qa_pair_collection_id } = data.value.results
    beforeAsk(
      qa_pair_collection_id, qaState.seriesId, query,
      type,
    )
    const collection = qaState.collection.find(item => item.id === qa_pair_collection_id)!
    completeOrReject(collection)

    await nextTick()
    scrollerContainer.value?.scroll({
      top: scrollerContainer.value?.scrollHeight + scrollerContainer.value.clientHeight,
      behavior: 'smooth',
    })
  }

  const getFileList = async (id: string) => {
    const { data, error } = await useGetQaFiles(id)
    if (error.value || !data.value)
      return

    qaState.docs = data.value.doc_list
  }

  const getSeries = async () => {
    if (!qaState.seriesId)
      return

    const { data, error } = await useGetQaSeries(qaState.seriesId)
    if (error.value || !data.value)
      return
    const qaSeries = data.value.results
    qaState.firstQuery = qaSeries.title
    if (qaSeries.qa_pair_collection_list.length > 0)
      qaState.mode = qaSeries.qa_pair_collection_list[0].latest_qa_pair?.search_mode === 'doc' ? QaMode.DOC : QaMode.WEB

    if (qaState.mode === 'doc')
      getFileList(qaState.seriesId)

    qaState.collection = qaSeries.qa_pair_collection_list.filter(i => i.latest_qa_pair).map((item) => {
      if (item.latest_qa_pair.qa_info) {
        const qa_info = (item.latest_qa_pair.qa_info as QaPairInfo)
        qa_info.ref_pages_list = []
        Object.keys(qa_info.ref_pages).forEach((key) => {
          qa_info.ref_pages_list.push(
            qa_info.ref_pages[key],
          )
        })
      }

      if (item.latest_qa_pair.reference) {
        item.latest_qa_pair.reference.forEach((r) => {
          if (r.poly) {
            const datas = r.poly.map((i: string) => i.split(','))
            r.polyDto = datas.map((i) => {
              return { page: Number(i[0]), poly: [Number(i[1]), Number(i[2]), Number(i[3]), Number(i[4])] }
            })
          }
        })
      }

      if (item.latest_qa_pair.general_answer && item.latest_qa_pair.reference && item.latest_qa_pair.reference.length > 0 && item.latest_qa_pair.qa_info)
        calcRefPageIndexByMode(item.latest_qa_pair.general_answer, item.latest_qa_pair.reference, item.latest_qa_pair.qa_info)

      if (item.latest_qa_pair.images && item.latest_qa_pair.images.length > 0 && item.latest_qa_pair.general_answer)
        item.latest_qa_pair.general_answer = replaceImgs(item.latest_qa_pair.images, item.latest_qa_pair.general_answer)

      if (item.latest_qa_pair.timeline_id?.events && item.latest_qa_pair.qa_info)
        replaceTimeRef(item.latest_qa_pair.timeline_id, item.latest_qa_pair.qa_info, item._id)

      if (item.latest_qa_pair.search_mode !== 'doc')
        qaState.mode = QaMode.WEB

      const collection = {
        progress: QaProgressState.Finish,
        id: item._id,
        query: item.query,
        is_subscribed: item.is_subscribed,
        pairsIds: item.qa_pair_list.reverse(),
        create_time: item.create_time,
        curPairId: item.latest_qa_pair._id,
        curTimelineSort: false,
        curDeleteNews: [],
        currentSearchMode: item.latest_qa_pair.search_mode as SearchModeType,
        pairs: [{
          _id: item.latest_qa_pair._id,
          version: item.latest_qa_pair.version,
          qa_info: item.latest_qa_pair.qa_info,
          general_answer: item.latest_qa_pair.general_answer || '',
          timeline_id: item.latest_qa_pair.timeline_id,
          recommend_query: item.latest_qa_pair.recommend_query,
          reference: item.latest_qa_pair.reference,
          images: item.latest_qa_pair.images || [],
          unsupported: item.latest_qa_pair.unsupported,
          search_mode: item.latest_qa_pair.search_mode,
        }],
      }
      return collection
    })
  }

  const stopCollection = async (collection_id?: string) => {
    if (!collection_id) {
      qaState.collection.forEach((i) => {
        i.controller?.abort()
      })
      return
    }

    const collection = qaState.collection.find(item => item.id === collection_id)
    if (!collection)
      return

    collection.controller?.abort()
    collection.controller = undefined
    collection.progress = QaProgressState.Finish
  }

  const reAsk = async (qa_pair_collection_id: string, type: QaAnswerType) => {
    const collection = qaState.collection.find(item => item.id === qa_pair_collection_id)
    if (!collection)
      return

    collection.progress = QaProgressState.Analyze
    collection.curType = type
    completeOrReject(collection)
  }

  const getPair = async (pair_id: string, collection_id: string) => {
    const { data, error } = await useGetQaPair(pair_id)
    if (error.value || !data.value)
      return

    const pair = data.value.results
    const collection = qaState.collection.find(item => item.id === collection_id)
    if (!collection)
      return

    if (pair.qa_info) {
      const qa_info = pair.qa_info as QaPairInfo
      qa_info.ref_pages_list = []
      Object.keys(qa_info.ref_pages).forEach((key) => {
        qa_info.ref_pages_list.push(
          qa_info.ref_pages[key],
        )
      })
      if (pair.reference) {
        pair.reference.forEach((r) => {
          if (r.poly) {
            const datas = r.poly.map((i: string) => i.split(','))
            r.polyDto = datas.map((i) => {
              return { page: Number(i[0]), poly: [Number(i[1]), Number(i[2]), Number(i[3]), Number(i[4])] }
            })
          }
        })
      }
    }

    if (pair.general_answer && pair.reference && pair.reference.length > 0 && pair.qa_info)
      calcRefPageIndexByMode(pair.general_answer, pair.reference, pair.qa_info)

    if (pair.images && pair.images.length > 0 && pair.general_answer)
      pair.general_answer = replaceImgs(pair.images, pair.general_answer)

    if (pair.timeline_id?.events && pair.qa_info)
      replaceTimeRef(pair.timeline_id, pair.qa_info, collection.id)

    collection.pairs.push(pair)
  }

  const pageHtml2Ref = (html: string, refs: AnswerRef[], pair: QaPair, coll: QaCollectionState) => {
    const news = pair.qa_info!.ref_pages_list

    if (!refs.forEach)
      return html
    const refs_ = refs.filter(i => html.includes(i._id))
    refs_.sort((x, y) => {
      return html.indexOf(x._id) - html.indexOf(y._id)
    })

    refs.forEach((ref) => {
      const newsIndex = news.findIndex(item => item._id === ref.news_id)
      if (newsIndex === -1)
        return

      const one = news[newsIndex]
      if (!one.index && qaState.mode === QaMode.WEB)
        return

      if (qaState.mode === QaMode.DOC) {
        const index = qaState.docs.findIndex(i => i._id === one._id) + 1
        if (index === 0)
          return
        else
          one.index = index
      }

      html = html.replaceAll(`${ref._id}`, `<span class="qa-ref" data-type="qa-content-ref" data-id="${one._id}" data-coll-id="${coll.id}" data-ref-id="${ref._id.slice(1, -1)}" data-pair-id="${pair._id}" >${one.index}</span>`)
    })

    return html
  }

  function calcRefPageIndex(html: string, refs: AnswerRef[], news: RefPage[] | RefDoc[], setDefault = true) {
    if (!refs.forEach)
      return
    const refs_ = refs.filter(i => html.includes(i._id))
    refs_.sort((x, y) => {
      return html.indexOf(x._id) - html.indexOf(y._id)
    })

    let index_ = 1
    const set = new Set<string>()
    refs_.forEach((ref) => {
      const pageIndex = news.findIndex(item => item._id === ref.news_id)

      if (pageIndex !== -1) {
        if (!set.has(news[pageIndex]._id)) {
          if (news[pageIndex].index === undefined)
            news[pageIndex].index = index_

          index_++
          set.add(news[pageIndex]._id)
        }
      }
    })

    if (setDefault) {
      news.sort((a, b) => {
        if (a.index !== undefined && b.index !== undefined)
          return a.index - b.index

        if (a.index === undefined)
          return 1

        if (b.index === undefined)
          return -1

        return 0
      })
      news.forEach((n, index) => {
        n.index = index + 1
      })
      news.forEach((item, index) => {
        item.index = index + 1
      })
    }
  }

  function calcRefPageIndexByMode(html: string, refs: AnswerRef[], info: QaPairInfo, setDefault = true) {
    if (qaState.mode === QaMode.WEB && info.ref_pages_list)
      calcRefPageIndex(html, refs, info.ref_pages_list, setDefault)
  }

  const subscribe = async (data: {
    push_interval: string
    push_time: string
    end_time: string
    email: string
    qa_pair_collection_id: string
  }) => {
    const collection = qaState.collection.find(item => item.id === data.qa_pair_collection_id)
    if (!collection)
      return
    const value = {
      ...data,
      qa_series_id: qaState.seriesId,
      query: collection.query,
    }
    const { error } = await usePostQaSubscribe(value)
    if (!error.value)
      collection.is_subscribed = true
  }

  return {
    createSeries,
    completeAsk,
    beforeAsk,
    reset,
    ask,
    setFirstQuery,
    completeOrReject,
    createPair,
    getSeries,
    stopCollection,
    createCollection,
    reAsk,
    getPair,
    pageHtml2Ref,
    subscribe,
    getFileList,
    qaState,
    scrollerContainer,
    scrollProgress,
  }
})

export {
  useQaStore,
}
