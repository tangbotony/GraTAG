export default defineNuxtRouteMiddleware((to) => {
  if (process.server)
    return

  if (!token.token) {
    const restPath = window.location.href.replace(window.location.origin, '')
    if (restPath === '/')
      return navigateTo('/login')
    else
      return navigateTo(`/login?from=${restPath}`)
  }
  else {
    if (to.path === '/')
      return navigateTo('/search')
  }
})
