export const WRITE_KIND = {
  Continue: 'continue',
  ContinuePro: 'continue_profession',
  Polish: 'polish',
  Expand: 'expand',
  Generate: 'generate',
  Title: 'title',
}

export const NEWS_KIND = {
  Review: 'review',
  Summarize: 'summarize',
  Message: 'message',
  Communication: 'communication',
  ExclusiveInterview: 'exclusive_interview',
  Feature: 'feature',
  Others: 'others',
}

export const NEWS_KIND_MAP: Record<string, string> = {
  review: '评论',
  summarize: '综述',
  message: '消息',
  communication: '通讯',
  exclusive_interview: '专访',
  feature: '特写',
  others: '其他稿件',
}

export const WRITE_STYLE = {
  STRICT: 'strict',
  TOUTIAO: 'toutiao',
  WEIXIN: 'weixin',
}

export const WRITE_STYLE_LIST = [
  { type: 'strict', title: '严肃风' },
  { type: 'toutiao', title: '头条风' },
  { type: 'weixin', title: '公众号风' },
]

export const WRITE_STYLE_MAP: Record<string, string> = {
  strict: '严肃风',
  toutiao: '头条风',
  weixin: '公众号风',
}

export const IMAGE_LIMIT_SIZE = 1024 * 1024 * 100
