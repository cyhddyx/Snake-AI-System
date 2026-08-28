import { snakeClient } from '../snake'
import type { AuthUser } from './auth'

export interface UserUpdate {
  username?: string
  email?: string
  avatar_url?: string
  role?: 'admin' | 'editor' | 'user'
  is_active?: boolean
}

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

export const usersApi = {
  list: () => snakeClient.get<AuthUser[]>('/users').then((res) => res.data),

  getById: (id: number) => snakeClient.get<AuthUser>(`/users/${id}`).then((res) => res.data),

  update: (id: number, data: UserUpdate) =>
    snakeClient.patch<AuthUser>(`/users/${id}`, data).then((res) => res.data),

  changePassword: (id: number, data: ChangePasswordRequest) =>
    snakeClient.post<{ message: string }>(`/users/${id}/change-password`, data).then((res) => res.data),

  remove: (id: number) => snakeClient.delete(`/users/${id}`),
}
