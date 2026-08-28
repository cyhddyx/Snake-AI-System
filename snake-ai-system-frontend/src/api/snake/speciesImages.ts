import { snakeClient } from '../snake'

export interface SpeciesImage {
  id: number
  species_id: number
  image_url: string
  thumbnail_url?: string
  caption?: string
  photographer?: string
  image_type: string
  sort_order: number
  is_cover: boolean
  created_at: string
}

export interface SpeciesImageCreate {
  species_id: number
  image_url: string
  thumbnail_url?: string
  caption?: string
  photographer?: string
  image_type?: string
  sort_order?: number
  is_cover?: boolean
}

export interface SpeciesImageUpdate {
  image_url?: string
  thumbnail_url?: string
  caption?: string
  photographer?: string
  image_type?: string
  sort_order?: number
  is_cover?: boolean
}

export const speciesImagesApi = {
  list: (speciesId: number) =>
    snakeClient.get<SpeciesImage[]>(`/species/${speciesId}/images`).then((res) => res.data),

  create: (speciesId: number, data: Omit<SpeciesImageCreate, 'species_id'>) =>
    snakeClient.post<SpeciesImage>(`/species/${speciesId}/images`, data).then((res) => res.data),

  update: (imageId: number, data: SpeciesImageUpdate) =>
    snakeClient.patch<SpeciesImage>(`/images/${imageId}`, data).then((res) => res.data),

  delete: (imageId: number) => snakeClient.delete(`/images/${imageId}`),
}
