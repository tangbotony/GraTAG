import type { FolderType } from './folder'

export interface QuoteRef {
  title: string
  url: string
  description: string[]
  id: string
  content: string
}

export interface FileType {
  _id: string
  update_time: number
  trash_time: number
  text: string
  plain_text: string
  type: string
  name: string
  parent_id: string
  path: [string, string][]
  editable: boolean
  reference: QuoteRef[]
  is_quote: boolean
}

export function useFile(id: string) {
  return useCustomFetch<{ doc: FileType; message: string }>(`/api/document/${id}`, {
    method: 'GET',
  })
}

export interface ResType {
  ext: string
  raw_file_path: string
  material_id: string
  material_name: string
}

interface materialArticleType {
  data: materialArticleData
}
interface materialArticleData {
  value: string
}
export function materialArticle(id: any) {
  return useCustomFetch<string>(`/api/material/preview/${id}`, {
    method: 'GET',
  })
}

interface FileCreateBody {
  name: string
  parent_id: string
  text: string
  plain_text: string
}

interface FileCreateResponse {
  doc_id: string
  message: string
}

export function useFileCreate(data: FileCreateBody) {
  return useCustomFetch<FileCreateResponse>('/api/document', {
    method: 'POST',
    body: data,
  })
}

interface FileUpdateBody {
  name?: string
  text?: string
  parent_id?: string
  plain_text?: string
  reference?: QuoteRef[]
  id: string
  is_quote?: boolean
}

interface FileUpdateResponse {
  message: string
  status: number
}

export function useFileUpdate(data: FileUpdateBody) {
  return useCustomFetch<FileUpdateResponse>('/api/document', {
    method: 'PUT',
    body: data,
  })
}

interface FileDeleteResponse {
  message: string
  status: number
}
export function useFileDelete(id: string) {
  return useCustomFetch<FileDeleteResponse>(`/api/document/${id}`, {
    method: 'DELETE',
  })
}

interface FileSearchBody {
  search_text: string
  parent_id: string
}

interface FileSearchResponse {
  message: string
  meta: (FolderType | FileType)[]
}

let fileSearchController: AbortController
export function useFileSearch(data: FileSearchBody) {
  fileSearchController?.abort?.()
  fileSearchController = new AbortController()
  return useCustomFetch<FileSearchResponse>('/api/search/document', {
    body: data,
    method: 'POST',
    signal: fileSearchController.signal,
  })
}
