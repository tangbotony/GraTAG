interface ImageUpdateResponse {
  image_url: string
  message: string
}

export function useImageUpload(file: File) {
  const formData = new FormData()
  formData.append('image', file)
  return useCustomFetch<ImageUpdateResponse>('/api/upload/image', {
    method: 'POST',
    body: formData,
  })
}
