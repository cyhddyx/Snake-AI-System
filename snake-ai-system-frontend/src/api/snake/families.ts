import { snakeClient } from '../snake'

export interface Family {
  id: number
  chinese_name: string
  latin_name: string
  description?: string
  created_at: string
}

export interface FamilyCreate {
  chinese_name: string
  latin_name: string
  description?: string
}

export interface FamilyUpdate {
  chinese_name?: string
  latin_name?: string
  description?: string
}

export const familiesApi = {
  list: () => snakeClient.get<Family[]>('/families').then((res) => res.data),

  get: (id: number) => snakeClient.get<Family>(`/families/${id}`).then((res) => res.data),

  create: (data: FamilyCreate) =>
    snakeClient.post<Family>('/families', data).then((res) => res.data),

  update: (id: number, data: FamilyUpdate) =>
    snakeClient.patch<Family>(`/families/${id}`, data).then((res) => res.data),

  delete: (id: number) => snakeClient.delete(`/families/${id}`),
}
