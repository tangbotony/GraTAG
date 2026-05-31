import type { FileType } from './file'
import type { FolderType } from './folder'

interface TrashResponse {
  message: string
}
export function useTrashRecoverFile(id: string) {
  return useCustomFetch<TrashResponse>(`/api/recover/document/${id}`, {
    method: 'GET',
  })
}

export function useTrashRecoverFolder(id: string) {
  return useCustomFetch<TrashResponse>(`/api/recover/folder/${id}`, {
    method: 'GET',
  })
}

interface TrashListResponse {
  message: string
  trash_file: (FileType & FolderType)[]
}

export function useTrashList() {
  return useCustomFetch<TrashListResponse>('/api/trash', {
    method: 'GET',
  })
}

export function useTrashDeleteDocument(id: string) {
  return useCustomFetch<TrashResponse>(`/api/trash/document/${id}`, {
    method: 'DELETE',
  })
}

export function useTrashDeleteFolder(id: string) {
  return useCustomFetch<TrashResponse>(`/api/trash/folder/${id}`, {
    method: 'DELETE',
  })
}

export function useTrashDeleteAll() {
  return useCustomFetch<TrashResponse>('/api/trash/all', {
    method: 'DELETE',
  })
}
