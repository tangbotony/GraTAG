// export const currentUser = useState<UserInfo | null>('user', () => null)
interface UserInfo {
  name: string
  access_type: string
  email: string
  passwd: string
  _id: string
  extend_data: Record<string, any>
}
export const currentUserLocalStorage = useLocalStorage('user', '')

export const currentUser: ComputedRef<UserInfo | null> = computed(() => {
  if (currentUserLocalStorage.value)
    return JSON.parse(currentUserLocalStorage.value) as UserInfo

  else
    return null
})

export async function updateUserInfo(key: string, value: any) {
  if (!currentUser.value?._id)
    return

  const user = JSON.parse(currentUserLocalStorage.value || '{}')
  if (!user.extend_data)
    user.extend_data = {}

  user.extend_data[key] = value
  currentUserLocalStorage.value = JSON.stringify(user)

  await useUpdateuser({
    extend_data: user.extend_data,
  }, currentUser.value?._id)
}
