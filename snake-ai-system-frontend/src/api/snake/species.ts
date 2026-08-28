import { snakeClient } from '../snake'

export type ToxicityLevel = '无毒' | '微毒' | '有毒' | '剧毒' | '极毒'
export type IUCNStatus = 'EX' | 'EW' | 'CR' | 'EN' | 'VU' | 'NT' | 'LC' | 'DD' | 'NE'

export interface Species {
  id: number
  genus_id: number
  chinese_name: string
  latin_name: string
  aliases?: string[]
  toxicity?: ToxicityLevel
  iucn_status?: IUCNStatus
  discoverer?: string
  discover_year?: number
  basic_intro?: string
  measurements?: Record<string, any>
  view_count: number
  created_at: string
  updated_at: string
}

export interface SpeciesCreate {
  genus_id: number
  chinese_name: string
  latin_name: string
  aliases?: string[]
  toxicity?: ToxicityLevel
  iucn_status?: IUCNStatus
  discoverer?: string
  discover_year?: number
  basic_intro?: string
  measurements?: Record<string, any>
}

export interface SpeciesUpdate {
  genus_id?: number
  chinese_name?: string
  latin_name?: string
  aliases?: string[]
  toxicity?: ToxicityLevel
  iucn_status?: IUCNStatus
  discoverer?: string
  discover_year?: number
  basic_intro?: string
  measurements?: Record<string, any>
}

export const speciesApi = {
  list: (genusId?: number) => {
    const params = genusId ? { genus_id: genusId } : {}
    return snakeClient.get<Species[]>('/species', { params }).then((res) => res.data)
  },

  get: (id: number) => snakeClient.get<Species>(`/species/${id}`).then((res) => res.data),

  create: (data: SpeciesCreate) =>
    snakeClient.post<Species>('/species', data).then((res) => res.data),

  update: (id: number, data: SpeciesUpdate) =>
    snakeClient.patch<Species>(`/species/${id}`, data).then((res) => res.data),

  delete: (id: number) => snakeClient.delete(`/species/${id}`),
}
