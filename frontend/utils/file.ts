import type { FileType } from '~/composables/api/file'
import type { FolderType } from '~/composables/api/folder'

export function formatterDate(row: FileType | FolderType) {
  const date = new Date(row.update_time)
  switch (getTimeStatus(date)) {
    case 'today':
      return `${formatDateNumber(date.getHours())}:${formatDateNumber(date.getMinutes())}`
    case 'currentyear':
      return `${formatDateNumber(date.getMonth() + 1)}月${formatDateNumber(date.getDate())}日 ${formatDateNumber(date.getHours())}:${formatDateNumber(date.getMinutes())}`
    case 'beforeyear':
      return `${formatDateNumber(date.getFullYear())}年${formatDateNumber(date.getMonth() + 1)}月${formatDateNumber(date.getDate())}日`
  }
}

