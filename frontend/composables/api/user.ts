interface UserInfo {
  message: string
  userinfo: {
    _id: string
    access_type: string
    email: string
    name: string
    passwd: string
  }
}

export function useFetchUser() {
  return useCustomFetch<UserInfo>('/api/user', {
    method: 'GET',
  }).then((res) => {
    if (res.data.value?.userinfo)
      currentUserLocalStorage.value = JSON.stringify(res.data.value?.userinfo)
  })
}

let updateUserController: AbortController | null = null

export function useUpdateuser(data: Record<string, any>, id: string) {
  if (updateUserController)
    updateUserController.abort()
  updateUserController = new AbortController()
  return useCustomFetch(`/api/user/${id}`, {
    method: 'POST',
    body: data,
    signal: updateUserController.signal,
  })
}
