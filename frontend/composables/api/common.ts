export function useGetDocSearch(id: string, type: string) {
  let contentType = 'application/json'
  if (type === 'txt')
    contentType = 'text/plain'
  if (type === 'pdf')
    contentType = 'application/pdf'

  return useCustomFetch<string>(`/api/doc_search/${id}`, {
    method: 'GET',
    headers: {
      'Content-Type': contentType,
    },
  })
}
