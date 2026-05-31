export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const urlObj = getRequestURL(event)
  const tokenKey = config.env === 'sit' ? 'token_dev' : 'token'
  const token = getCookie(event, tokenKey)

  if (urlObj.pathname === '/login' && token)
    await sendRedirect(event, '/search')
})
