import { snakeClient } from '../snake'

export interface SpeciesContent {
  id: number
  species_id: number
  zoology?: string
  history?: string
  morphology?: string
  distribution?: string
  habitat?: string
  behavior?: string
  reproduction?: string
  conservation?: string
  value?: string
  hazard?: string
  content_format: string
  updated_at: string
}

export interface SpeciesContentCreate {
  species_id: number
  zoology?: string
  history?: string
  morphology?: string
  distribution?: string
  habitat?: string
  behavior?: string
  reproduction?: string
  conservation?: string
  value?: string
  hazard?: string
  content_format?: string
}

export interface SpeciesContentUpdate {
  zoology?: string
  history?: string
  morphology?: string
  distribution?: string
  habitat?: string
  behavior?: string
  reproduction?: string
  conservation?: string
  value?: string
  hazard?: string
  content_format?: string
}

export const speciesContentApi = {
  get: (speciesId: number) =>
    snakeClient.get<SpeciesContent>(`/species/${speciesId}/content`).then((res) => res.data),

  create: (speciesId: number, data: Omit<SpeciesContentCreate, 'species_id'>) =>
    snakeClient.post<SpeciesContent>(`/species/${speciesId}/content`, data).then((res) => res.data),

  update: (speciesId: number, data: SpeciesContentUpdate) =>
    snakeClient
      .patch<SpeciesContent>(`/species/${speciesId}/content`, data)
      .then((res) => res.data),

  delete: (speciesId: number) => snakeClient.delete(`/species/${speciesId}/content`),
}
