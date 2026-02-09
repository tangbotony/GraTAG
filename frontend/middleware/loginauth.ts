export default defineNuxtRouteMiddleware((to) => {
  if (process.server)
    return

  if (token.token)
    return navigateTo('/search')
})
