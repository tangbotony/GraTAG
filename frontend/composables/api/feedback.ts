interface FeedbackBody {
  pic_list?: string[]
  brief?: string
  description?: string
  contact?: string
  type: string
}

export function useFeedback(data: FeedbackBody) {
  return useCustomFetch('/api/feedback', {
    method: 'POST',
    body: data,
  })
}
