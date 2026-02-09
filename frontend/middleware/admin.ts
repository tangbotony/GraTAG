export default defineNuxtRouteMiddleware((to) => {
  if (process.server)
    return

  const accessType = currentUser.value?.access_type
  const kinds = ['admin', 'super_admin']
  if (to.path === '/admin') {
    if (!accessType)
      return navigateTo('/file')

    if (accessType && !kinds.includes(accessType))
      return navigateTo('/file')
  }
})
