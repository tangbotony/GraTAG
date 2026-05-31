import type { FileType } from './api/file'
import type { FolderType } from './api/folder'

interface FileState {
  currentFolder: string
  currentData: (FileType | FolderType)[]
  stack: [string, string][]
}

export const fileState = useState<FileState>('file', () => {
  return {
    currentFolder: '-1',
    currentData: [],
    stack: [['-1', 'root']],
  }
})

export const filePending = ref(false)

async function getData() {
  filePending.value = true
  const { data, error } = await useFetchFolder(fileState.value.currentFolder || '-1')
  filePending.value = false
  if (!error.value && data.value?.meta)
    fileState.value.currentData = data.value.meta
}

export async function refreshFolder() {
  await getData()
}

export function moveFilePath(path: [string, string][], to: [string, string], isFetching = true) {
  const index = fileState.value.stack.findIndex(s => s[0] === to[0])
  if (index === -1) {
    fileState.value.stack = [...path]
    fileState.value.currentFolder = to[0]
  }
  else {
    fileState.value.stack = fileState.value.stack.slice(0, index + 1)
    fileState.value.currentFolder = to[0]
  }

  if (isFetching)
    getData()
}

export function pushFilePath(to: [string, string]) {
  fileState.value.stack.push(to)
  fileState.value.currentFolder = to[0]
  getData()
}
