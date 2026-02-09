import { defu } from 'defu'
import type { FetchOptions, FetchResponse } from 'ofetch'
import { ofetch } from 'ofetch'
import Token from '~/lib/token'
import { Stream } from '~/lib/streaming'

const isEnv = import.meta.env.VITE_ENV === 'sit'
export const token = new Token(isEnv ? 'dev' : 'prod')
const baseURL = import.meta.env.VITE_API

let isRefreshing = false
let requestQueue: {
  resolve: (value: unknown) => void
  reject: (reason?: any) => void
}[] = []

let errorMessage = ''
let errorStatusCode = ''
let errorPath = ''
let errorRes: undefined | FetchResponse<any>

async function beforeFetch(url: string, fetchOptions: FetchOptions = {}) {
  if (isRefreshing && !url.endsWith('/api/refresh')) {
    try {
      await new Promise((resolve, reject) => {
        requestQueue.push({ resolve, reject })
      })
    }
    catch (error) {
      return Promise.reject(error)
    }
  }

  const defaults: FetchOptions = {
    baseURL,
    onRequest({ request, options }) {
      if (request !== '/api/login' && request !== '/api/refresh' && request !== '/api/logout_batch' && token.token) {
        options.headers = options.headers
          ? {
              ...options.headers,
              Authorization: `Bearer ${token.token}`,
            }
          : {
              Authorization: `Bearer ${token.token}`,
            }
      }
      // options.headers = {
      //   ...options.headers,
      //   'X-Request-Id': getRandomString(),
      // }
    },

    onRequestError(_ctx) {
      if (_ctx.error.name !== 'AbortError')
        errorMessage = _ctx.error.message
    },

    onResponse(_ctx) {
      const isError = _ctx.response.ok === false
      if (isError)
        return
      const url = new URL(_ctx.request.toString())
      if (url.pathname.endsWith('/api/login')) {
        token.setToken(_ctx.response._data.access_token)
        token.setRefreshToken(_ctx.response._data.refresh_token)
        const route = useRoute()
        const router = useRouter()
        if (route.query.from)
          router.push(route.query.from as string)

        else
          navigateTo('/search')
      }
      else if (url.pathname.endsWith('/api/logout')) {
        token.removeToken()
        token.removeRefreshToken()
        navigateTo('/login')
      }
      else if (url.pathname.endsWith('/api/refresh')) {
        token.setToken(_ctx.response._data.access_token)
      }
    },

    onResponseError(_ctx) {
      if (!_ctx.response.ok) {
        errorMessage = _ctx.response._data.message || _ctx.response._data.msg || _ctx.response.statusText
        errorStatusCode = String(_ctx.response.status)
        errorPath = new URL(_ctx.response.url).pathname
        errorRes = _ctx.response
      }
    },
  }

  return {
    defaults,
  }
}

function useCustomFetch<T>(
  url: string,
  options: FetchOptions = {},
  useAsyncDataOptions = {},
) {
  return useAsyncData(getRandomString(), async () => {
    const { defaults } = await beforeFetch(url, options)

    // for nice deep defaults, please use unjs/defu
    const params = defu(defaults, options)

    try {
      const res = await ofetch<T>(url, params as FetchOptions<'json'>)
      return res
    }
    catch (error_) {
      if (errorStatusCode === '401' && !url.endsWith('/api/login') && !url.endsWith('/api/refresh')) {
        try {
          isRefreshing = true
          const { error } = await useCustomFetch('/api/refresh', {
            method: 'GET',
            headers: { Authorization: `Bearer ${token.refreshToken}` },
          })
          if (error.value)
            throw error.value

          requestQueue.forEach(req => req.resolve(null))
          const res = await ofetch<T>(url, params as FetchOptions<'json'>)
          return res
        }
        catch (e) {
          token.removeToken()
          token.removeRefreshToken()
          requestQueue.forEach(req => req.reject())
          goLoginPageWithUrl()
          return Promise.reject(e)
        }
        finally {
          isRefreshing = false
          requestQueue = []
        }
      }
      else if (errorStatusCode === '422' || errorStatusCode === '408') {
        if (!url.endsWith('/api/refresh')) {
          ElMessage({
            message: errorMessage || '未知错误',
            type: 'error',
            customClass: 'req-message',
          })
        }
        token.removeToken()
        token.removeRefreshToken()
        goLoginPageWithUrl()
        return Promise.reject(error_)
      }
      else if (errorStatusCode === '423') {
        await dealMaxDevice(errorRes?._data.last_tokens, errorRes?._data.message, url, params as FetchOptions<'json'>)
      }
      else {
        if (errorMessage) {
          if (!url.endsWith('/api/refresh')) {
            ElMessage({
              message: errorMessage,
              type: 'error',
              customClass: 'req-message',
            })
          }
        }
        return Promise.reject(error_)
      }
    }
    finally {
      errorMessage = ''
      errorStatusCode = ''
      errorPath = ''
      errorRes = undefined
    }
  }, useAsyncDataOptions)
}

async function useCustomStream<T>(
  url: string,
  options: { controller: AbortController } & FetchOptions,
) {
  const { defaults } = await beforeFetch(url)

  const { controller, ...rest } = options
  const params = defu(defaults, rest, { responseType: 'stream', timeout: 1000 * 60 * 10, signal: controller.signal })
  const res = await ofetch<T, 'stream'>(url, params as FetchOptions<'stream'>)
  return Stream.fromSSEResponse<T>(res as ReadableStream<Uint8Array>, controller)
}

function goLoginPageWithUrl() {
  const restPath = window.location.href.replace(window.location.origin, '')
  if (window.location.pathname.endsWith('/login'))
    return

  if (restPath === '/')
    navigateTo('/login')

  else
    navigateTo(`/login?from=${encodeURIComponent(restPath)}`)
}

let isDealMaxDevice = false
function dealMaxDevice(token: string[], message: string, url: string, params: FetchOptions<'json'>) {
  if (isDealMaxDevice)
    return

  isDealMaxDevice = true
  return ElMessageBox.confirm(
    message,
    '',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'error',
      customClass: 'message-box-container',
    },
  ).then(async () => {
    await useLogoutBatch(token)
    if (url.endsWith('/api/login'))
      await ofetch(url, params as FetchOptions<'json'>)

    if (!url.endsWith('/api/login'))
      location.reload()
  }).finally(() => {
    isDealMaxDevice = false
  })
}

export {
  useCustomFetch,
  useCustomStream,
}
