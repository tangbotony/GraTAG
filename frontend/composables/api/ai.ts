export interface Quote {
  title: string
  url: string
  description: string
  id: string
  content: string
}

export interface QuoteRes {
  write_text: string
  ref_item: {
    [key: string]: Quote
  }
}

interface ContinueWritingBody {
  selected_content: string
  context_above: string
  context_below: string
  doc_id: string
  page_title: string
}

export function useAiContinueWriting(data: ContinueWritingBody, options: { signal: AbortSignal }) {
  return useCustomFetch<{ result: string[] }>('/api/ai/basic_continue_write', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    signal: options.signal,
  })
}

export function useAiContinueWritingQuote(data: ContinueWritingBody, options: { signal: AbortSignal }) {
  return useCustomFetch<{ result: QuoteRes[] }>('/api/ai/basic_continue_write_reference', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    signal: options.signal,
  })
}

interface ProContinueWritingBody {
  selected_content: string
  context_above: string
  context_below: string
  doc_id: string
  output_num?: number
  pro_setting_continue_direction: {
    [key: string]: string
  }
  pro_setting_special_request?: string
  pro_setting_language_type: string
  pro_setting_length: string
  page_title: string
}

export function useAiProContinueWriting(data: ProContinueWritingBody, options: { signal: AbortSignal }) {
  return useCustomFetch<{ result: string[] }>('/api/ai/pro_continue_write', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    ...options,
  })
}

export function useAiProContinueWritingQuote(data: ProContinueWritingBody, options: { signal: AbortSignal }) {
  return useCustomFetch<{ result: QuoteRes[] }>('/api/ai/pro_continue_write_reference', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    ...options,
  })
}

interface ExpandWritingBody {
  selected_content: string
  context_above: string
  context_below: string
  doc_id: string
  page_title: string
}

export function useAiExpandWriting(data: ExpandWritingBody, options: { signal: AbortSignal }) {
  return useCustomFetch<{ result: string[] }>('/api/ai/basic_expand_write', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    signal: options.signal,
  })
}

interface PolishWritingBody {
  selected_content: string
  context_above: string
  context_below: string
  polish_type: string
  doc_id: string
  page_title: string
  style: string
}

export function useAiPolishWriting(data: PolishWritingBody, options: { signal: AbortSignal }) {
  return useCustomFetch<{ result: string[] }>('/api/ai/basic_polish_write', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    signal: options.signal,
  })
}

interface TitleBody {
  selected_content: string
  doc_id: string
  style: string
}

export function useAiTitle(data: TitleBody, opinion: { signal: AbortSignal }) {
  return useCustomFetch<{ result: string }>('/api/ai/basic_article2title', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    signal: opinion.signal,
  })
}
interface pointDataType {
  title: string
  title_ori: string
}
interface SubTitle {
  topic?: string
  material_id: string[]
  sub_title_his: pointDataType[]
  require?: string
  session_id: string
  kind: string
  style: string
  direction?: string
}
export function generateSubTitle(data: SubTitle, options: { signal: AbortSignal }) {
  return useCustomFetch<{ result: any }>('/api/ai/material/generate_sub_title', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    signal: options.signal,
  })
}

interface Review {
  topic: string
  material_id: string[]
  sub_title: string[]
  result_his: string[]
  review_length: number
  use_trusted_website: boolean
  kind: string
  style: string
  direction?: string
}

interface Quote1 {
  [key: string]: Quote2
}
interface Quote2 {
  ext: string
  material_id: string
  material_name: string
  raw_file_path: string
}
export interface Quote3 {
  title: string
  write_text: string
  ref_item: Quote4
}
interface Quote4 {
  [key: string]: Quote5
}
interface Quote5 {
  content: string
  description: string
  id: string
  title: string
  url: string
  source: string
  source_id: string
  source_name: string
  key: string
  index: number
  pos: number
}
export interface sucRes {
  materials: Quote1
  review: Quote3
}
export function generateReview(data: Review, options: { signal: AbortSignal }) {
  return useCustomFetch<{ result: sucRes }>('/api/ai/material/generate_review', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    signal: options.signal,
  })
}
