import type { FolderType } from './api/folder'
import type { FileType } from './api/file'

interface TrashState {
  currentData: (FileType | FolderType)[]
}

export const trashState = useState<TrashState>('trash', () => {
  return {
    currentData: [],
  }
})

export const trashPending = ref(false)

export async function fetchTrash() {
  trashPending.value = true
  const { data, error } = await useTrashList()
  trashPending.value = false
  if (!error.value)
    trashState.value.currentData = data.value?.trash_file || []
}
