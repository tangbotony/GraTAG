interface AddUserBody {
  name: string
  passwd: string
  create_date: string
  expire_date: string
  department: string
  real_name?: string
  phone?: string
  max_devices?: number
  remark?: string
}

export interface User {
  _id: string
  name: string
  passwd: string
  create_date: string
  expire_date: string
  department: string
  real_name?: string
  phone?: string
  creator?: string
  last_login?: string
  max_devices?: number
  remark?: string
}

export function useAddUser(data: AddUserBody) {
  return useCustomFetch<{ res: string }>('/api/admin/add_user', {
    method: 'POST',
    body: {
      ...data,
      access_type: 'normal',
    },
  })
}

interface UpdateUserBody {
  _id: string
  name?: string
  passwd?: string
  create_date?: string
  expire_date?: string
  department?: string
  real_name?: string
  phone?: string
  max_devices?: number
  remark?: string
}

export function useUpdateUser(data: UpdateUserBody) {
  return useCustomFetch<{ res: string }>('/api/admin/modify_user', {
    method: 'PUT',
    body: {
      ...data,
    },
  })
}

export function useDeleUser(data: { _id: string }) {
  return useCustomFetch<{ res: string }>('/api/admin/delete_user', {
    method: 'DELETE',
    body: {
      ...data,
    },
  })
}

export function useListUsers() {
  return useCustomFetch<{ res: User[] }>('/api/admin/list_user')
}
