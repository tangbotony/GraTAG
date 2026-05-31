export function useAiGenRecentEvent() {
  return useCustomFetch<{
    result: {
      event_argument: string
      event_desc: string
      event_evidence: string
    }
  }>('/api/ai/comment/generate_recent_event', {
    method: 'POST',
    body: {
      request_id: getRandomString(),
    },
  })
}

export function useAiGenSearch(data: { search: string; event_id: string }) {
  return useCustomFetch<{
    result: {
      title: string
      abstract: string
      url: string
    }[]
  }>('/api/ai/comment/generate_search', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
  })
}

export function useAiGenGeneralArgument(data: {
  event_id: string
  event: string
  title: string
  user_title: string
  abstract: string
  require?: string
  arguments: {
    opinion: string
    evidence: string
  }[]
}, options: { signal: AbortSignal }) {
  return useCustomFetch<{
    result: string[]
  }>('/api/ai/comment/generate_general_argument', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    signal: options.signal,
  })
}

interface GenBaseBody {
  event_id: string
  generalArgument: string
  generalArgumentFix: string
  event: string
  title: string
  user_title: string
  abstract: string
  require?: string
  arguments: {
    opinion: string
    evidence: string
  }[]
  structrue: string
  generate_arguments?: {
    [key: string]: {
      opinion: string
      evidence: string
      status: boolean
      reference_index: number }
  }
  argument_history: { [key: string]: any }
  current_page: string
}

export function useAiGenArgumentEvidence(data: GenBaseBody, options: { signal: AbortSignal }) {
  return useCustomFetch<{
    result: {
      opinion: string
      evidence: string
      reference_index: number
    }[]
  }>('/api/ai/comment/generate_argument_evidence', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    signal: options.signal,
  })
}

export function useAiGenEvidence(
  data: GenBaseBody & { currentArgument: { opinion: string; evidence: string; status: boolean; reference_index: number; index: string } },
  options: { signal: AbortSignal },
) {
  return useCustomFetch<{
    result: string
  }>('/api/ai/comment/generate_evidence', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    signal: options.signal,
  })
}

export function useAiGenArticle(
  data: Omit<GenBaseBody, 'current_page'>,
  options: { signal: AbortSignal },
) {
  return useCustomFetch<{
    result: {
      content: string
      title: string
    }
  }>('/api/ai/comment/generate_article', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    signal: options.signal,
  })
}

export function useAiGenTitle(
  data: Omit<GenBaseBody, 'current_page'> & {
    title_lists: string[]
    context: string
  },
  options: { signal: AbortSignal },
) {
  return useCustomFetch<{
    result: string
  }>('/api/ai/comment/generate_title', {
    method: 'POST',
    body: {
      ...data,
      request_id: getRandomString(),
    },
    signal: options.signal,
  })
}
