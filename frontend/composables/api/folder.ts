import type { FileType } from './file'

export interface FolderType {
  _id: string
  update_time: string
  name: string
  type: string
  parent_id: string
  path: [string, string][]
  trash_time: number
}

export function useFetchFolder(id: string) {
  return useCustomFetch<{
    message: string
    meta: (FolderType | FileType)[]
  }>(`/api/folder/${id}`, {
        method: 'GET',
      })
}

interface FoldCreateBody {
  name?: string
  parent_id?: string
}

interface FoldCreateResponse {
  folder_id: string
  message: string
}

export function useFolderCreate(data: FoldCreateBody) {
  return useCustomFetch<FoldCreateResponse>('/api/folder', {
    method: 'POST',
    body: data,
  })
}

interface FoldUpdateBody {
  id: string
  name?: string
  parent_id?: string
}

interface FoldUpdateResponse {
  message: string
  status: number
}

export function useFolderUpdate(data: FoldUpdateBody) {
  return useCustomFetch<FoldUpdateResponse>('/api/folder', {
    method: 'PUT',
    body: data,
  })
}

interface FoldDeleteResponse {
  message: string
  status: number
}

export function useFolderDelete(id: string) {
  return useCustomFetch<FoldDeleteResponse>(`/api/folder/${id}`, {
    method: 'DELETE',
  })
}
