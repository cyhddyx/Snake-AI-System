import { snakeClient } from '../snake'

export type UserRole = 'admin' | 'editor' | 'user'

export interface AuthUser {
  id: number
  username: string
  email: string
  avatar_url?: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  username_or_email: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: AuthUser
}

export interface UserFavorite {
  id: number
  user_id: number
  species_id: number
  created_at: string
}

export const authApi = {
  login: (data: LoginRequest) => snakeClient.post<TokenResponse>('/auth/login', data).then((res) => res.data),
  me: () => snakeClient.get<AuthUser>('/auth/me').then((res) => res.data),
  register: (data: RegisterRequest) => snakeClient.post<AuthUser>('/users/register', data).then((res) => res.data),
}

export const userFavoritesApi = {
  list: (userId: number) =>
    snakeClient.get<UserFavorite[]>(`/users/${userId}/favorites`).then((res) => res.data),
  add: (userId: number, speciesId: number) =>
    snakeClient.post<UserFavorite>(`/users/${userId}/favorites`, { species_id: speciesId }).then((res) => res.data),
  remove: (userId: number, speciesId: number) =>
    snakeClient.delete(`/users/${userId}/favorites/${speciesId}`),
  check: (userId: number, speciesId: number) =>
    snakeClient.get<{ is_favorited: boolean }>(`/users/${userId}/favorites/check/${speciesId}`).then((res) => res.data),
}
