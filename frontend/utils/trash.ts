import type { FileType } from '~/composables/api/file'
import type { FolderType } from '~/composables/api/folder'

export function formatterRemainDate(row: FileType | FolderType) {
  const trashDate = new Date(row.trash_time)
  const now = new Date()
  const remainDays = Math.floor((trashDate.getTime() - now.getTime()) / (24 * 3600 * 1000))
  return `${remainDays}天`
}
