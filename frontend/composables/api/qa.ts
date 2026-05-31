// ------------------- QA Search -------------------
export function useGetQaSearchHistory() {
  return useCustomFetch<{ results: { _id: string; title: string; create_time: string }[] }>('/api/qa/search/history', {
    method: 'GET',
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

export function useDeleteQaSearchHistories() {
  return useCustomFetch('/api/qa/search/history', {
    method: 'Delete',
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

export function useDeleteQaSearchHistory(id: string) {
  return useCustomFetch(`/api/qa/search/history/${id}`, {
    method: 'Delete',
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}
let qaSearchController: AbortController
export function useGetQaSearchCompletion(query: string) {
  qaSearchController?.abort?.()
  qaSearchController = new AbortController()
  return useCustomFetch<{ results: string[] }>('/api/qa/search/completion', {
    query: {
      q: query,
    },
    method: 'GET',
    signal: qaSearchController.signal,
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

// ------------------- QA Series-------------------

export function useGetQaSearchRecom() {
  return useCustomFetch<{ results: string[] }>('/api/qa/recommend', {
    method: 'GET',
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

export interface QaHistoryRecord {
  _id: string
  is_subscribe: boolean
  title: string
  create_time: string
}

export function useGetQaHistory() {
  return useCustomFetch<{
    results: QaHistoryRecord[]
  }>('/api/qa/history', {
    method: 'GET',
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

interface QaSeries {
  _id: string
  title: string
  qa_pair_collection_list: QaCollection[]
}

export interface QaCollection {
  _id: string
  query: string
  is_subscribed: boolean
  latest_qa_pair: QaPair
  qa_pair_list: string[]
  create_time: string
}

export interface QaPair {
  _id: string
  query?: string
  version?: number
  qa_info?: QaPairInfo
  general_answer?: string
  timeline_id?: QaTimeline
  recommend_query?: string[]
  reference?: AnswerRef[]
  images?: { id: string; url: string; origin_doc_url: string }[]
  unsupported: number
  search_mode: string
}

export interface QaTimeline {
  is_multi_subject: boolean
  events: {
    title?: string
    img?: string
    index?: number
    event_list: {
      start_time: string
      end_tiem?: string
      img: string
      event_subject: string
      main_character?: string
      location?: string
      event_abstract: string
      event_abstract_html: string
      event_title: string
      reference_object: {
        [key: string]: {
          url: string
          title: string
          _id: string
          content: string
          icon: string
          news_id: string
        }
      }
      direc?: string
      start_time_obj?: {
        year: string
        month: string
        day: string
      }
    }[]
  }[]
}

export interface QaPairInfo {
  site_num: number
  page_num: number
  word_num: number
  doc_num: number
  additional_query: QaAdditionQuery
  search_query: string[]
  ref_pages_list: RefPage[]
  ref_pages: {
    [key: string]: RefPage
  }
  ref_docs_list: RefDoc[]
  ref_docs: {
    [key: string]: RefDoc
  }
}

export interface AnswerRef {
  _id: string
  news_id: string
  content: string[]
  origin_content: string[]
  poly?: string[]
  polyDto?: { page: number; poly: [number, number, number, number] }[]
}

export interface QaAdditionQuery {
  title: string
  options: string[]
  selected_option: string[]
  other_option: string
}

export interface RefPage {
  _id: string
  url: string
  site: string
  title: string
  summary: string
  content: string
  icon: string
  index?: number
}

export interface RefDoc {
  _id: string
  doc_name: string
  index?: number
}

export function useGetQaSeries(qa_series_id: string) {
  return useCustomFetch<{ results: QaSeries }>(`/api/qa/series/${qa_series_id}`, {
    method: 'GET',
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

export function useDeleteQaSeriesDelete(qa_series_id: string) {
  return useCustomFetch(`/api/qa/series/${qa_series_id}`, {
    method: 'Delete',
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

export function usePostQaSeries(query: string, doc_id_list?: string[]) {
  const body: { title: string; doc_id_list?: string[] } = {
    title: query,
  }
  if (doc_id_list)
    body.doc_id_list = doc_id_list

  return useCustomFetch<{
    results: {
      qa_series_id: string
      qa_pair_collection_id: string
    }
  }>('/api/qa/series', {
    method: 'POST',
    body,
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

export function useAddQaPair(query: string, qa_series_id: string, qa_pair_collection_id: string, search_mode: string) {
  return useCustomFetch<{
    results: {
      qa_pair_id: string
    }
  }>('/api/qa/pair/create', {
    method: 'POST',
    body: {
      query,
      qa_series_id,
      qa_pair_collection_id,
      search_mode,
    },
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

export function usePostQaCollection(id: string) {
  return useCustomFetch<{
    results: {
      qa_series_id: string
      qa_pair_collection_id: string
    }
  }>('/api/qa/collection', {
    body: {
      qa_series_id: id,
    },
    method: 'POST',
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

type QaAskType = 'first' | 'append' | 're_generate' | 'subscription' | 'delete_ref' | 'recommend'
export enum QaAskCompleteResType {
  Reject = 'reject',
  None = 'none',
  AdditionalQuery = 'additional_query',
}

export interface QaCompleteRes {
  type: QaAskCompleteResType
  additional_query?: QaAdditionQuery
  qa_pair_id: string
  unsupported: number
}

export function usePostQaCompleteAsk(
  data: {
    qa_series_id: string
    qa_pair_collection_id: string
    query: string
    type: QaAskType
    search_mode: string
  },
  signal: AbortSignal,
) {
  return useCustomFetch<{ results: QaCompleteRes }>('/api/qa/complete/ask', {
    method: 'POST',
    body: data,
    signal,
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

export interface QaAskState {
  type: string
  data: 'analyze' | 'search' | 'organize' | 'complete'
  query: string
  qa_series_id: string
  qa_pair_collection_id: string
  qa_pair_id: string
  version: number
}

interface QaAskPairInfo {
  type: string
  data: QaPairInfo
  query: string
  qa_series_id: string
  qa_pair_collection_id: string
  qa_pair_id: string
}

interface QaAskText {
  type: string
  data: string
  query: string
  qa_series_id: string
  qa_pair_collection_id: string
  qa_pair_id: string
}

interface QaAskRefAnswer {
  type: string
  data: AnswerRef[]
  query: string
  qa_series_id: string
  qa_pair_collection_id: string
  qa_pair_id: string
}

interface QaAskRecom {
  type: string
  data: string[]
  query: string
  qa_series_id: string
  qa_pair_collection_id: string
  qa_pair_id: string
}

interface QaAskTimeline {
  type: string
  data: QaTimeline
}

export interface QaAskImg {
  type: string
  data: {
    id: string
    url: string
    origin_doc_url: string
  }[]
}

export interface QaAskTextEnd {
  type: string
  data: {

  }
}

export function usePostQaAsk(
  data: {
    qa_series_id: string
    qa_pair_collection_id: string
    query: string
    qa_pair_id: string
    type: QaAskType
    delete_news_list: string[]
    additional_query?: QaAdditionQuery
    search_mode: string
  },
  controller: AbortController,
) {
  return useCustomStream<{
    results: QaAskRecom | QaAskRefAnswer | QaAskText | QaAskPairInfo | QaAskState | QaAskTimeline | QaAskImg | QaAskTextEnd
  }>('/api/qa/ask', {
    method: 'POST',
    body: data,
    controller,
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

export function useGetQaPair(qa_pair_id: string) {
  return useCustomFetch<{ results: QaPair }>(`/api/qa/pair/${qa_pair_id}`, {
    method: 'GET',
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

// --- sub ---
interface QaSubscribeBody {
  qa_series_id: string
  qa_pair_collection_id: string
  push_interval: string
  push_time: string
  end_time: string
  email: string
  query: string
}
export function usePostQaSubscribe(body: QaSubscribeBody) {
  return useCustomFetch<{ results: { stauts: boolean } }>('/api/qa/subscribe', {
    method: 'POST',
    body,
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

export function useDeleteQaSubscribe(body: { qa_pair_collection_id: string }) {
  return useCustomFetch('/api/qa/subscribe', {
    body,
    method: 'Delete',
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

export interface QaDoc {
  _id: string
  qa_series_id: string
  size: number
  name: string
  format: string
  selected: boolean
  date: string
}

export function useGetQaFiles(id: string) {
  return useCustomFetch<{ doc_list: QaDoc[] }>(`/api/doc_search/doc_list/${id}`, {
    method: 'GET',
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

export function useUpdateQaDocSelect(id: string, seriesId: string, selected: boolean) {
  return useCustomFetch('/api/doc_search/update_select', {
    method: 'PUT',
    body: {
      doc_id: id,
      qa_series_id: seriesId,
      selected,
    },
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}

export function useDeleteQaDoc(id: string, seriesId: string) {
  return useCustomFetch('/api/doc_search/doc', {
    method: 'Delete',
    body: {
      doc_id: id,
      qa_series_id: seriesId,
    },
    headers: {
      'X-Request-Id': getRandomString(),
    },
  })
}
