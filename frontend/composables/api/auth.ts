import md5 from 'md5'

interface LoginResponse {
  access_token: string
  refresh_token: string
}

export function useLogin(username: string, password: string) {
  return useCustomFetch<LoginResponse>('/api/login', {
    method: 'POST',
    body: {
      name: username,
      passwd: md5(password),
    },
  })
}

export function useLogout() {
  return useCustomFetch('/api/logout', {
    method: 'POST',
  })
}

export function useLogoutBatch(token: string[]) {
  return useCustomFetch('/api/logout_batch', {
    method: 'POST',
    body: {
      logout_tokens: token,
    },
  })
}
