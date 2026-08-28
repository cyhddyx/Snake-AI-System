import { snakeClient } from '../snake'

export interface Genus {
  id: number
  family_id: number
  chinese_name: string
  latin_name: string
  description?: string
  created_at: string
}

export interface GenusCreate {
  family_id: number
  chinese_name: string
  latin_name: string
  description?: string
}

export interface GenusUpdate {
  family_id?: number
  chinese_name?: string
  latin_name?: string
  description?: string
}

export const generaApi = {
  list: (familyId?: number) => {
    const params = familyId ? { family_id: familyId } : {}
    return snakeClient.get<Genus[]>('/genera', { params }).then((res) => res.data)
  },

  get: (id: number) => snakeClient.get<Genus>(`/genera/${id}`).then((res) => res.data),

  create: (data: GenusCreate) => snakeClient.post<Genus>('/genera', data).then((res) => res.data),

  update: (id: number, data: GenusUpdate) =>
    snakeClient.patch<Genus>(`/genera/${id}`, data).then((res) => res.data),

  delete: (id: number) => snakeClient.delete(`/genera/${id}`),
}
