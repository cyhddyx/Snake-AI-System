import { snakeClient } from '../snake'
import type { IUCNStatus, ToxicityLevel } from './species'

export type SubmissionStatus = 'pending' | 'approved' | 'rejected'

export interface SubmissionImage {
  image_url: string
  thumbnail_url?: string
  caption?: string
  photographer?: string
  image_type: string
  sort_order: number
  is_cover: boolean
}

export interface SpeciesSubmission {
  id: number
  submitter_id: number
  reviewer_id?: number | null
  genus_id: number
  chinese_name: string
  latin_name: string
  target_species_id?: number | null
  aliases?: string[]
  toxicity?: ToxicityLevel
  iucn_status?: IUCNStatus
  discoverer?: string
  discover_year?: number
  basic_intro?: string
  measurements?: Record<string, any>
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
  images: SubmissionImage[]
  review_note?: string | null
  status: SubmissionStatus
  created_species_id?: number | null
  created_at: string
  updated_at: string
  reviewed_at?: string | null
}

export interface SpeciesSubmissionCreate {
  genus_id: number
  chinese_name: string
  latin_name: string
  target_species_id?: number | null
  aliases?: string[]
  toxicity?: ToxicityLevel
  iucn_status?: IUCNStatus
  discoverer?: string
  discover_year?: number
  basic_intro?: string
  measurements?: Record<string, any>
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
  images?: SubmissionImage[]
}

export type SpeciesSubmissionUpdate = Partial<SpeciesSubmissionCreate>

export interface SpeciesSubmissionReview {
  review_note?: string
}

export const submissionsApi = {
  list: (params?: { status?: SubmissionStatus; mine_only?: boolean }) =>
    snakeClient
      .get<SpeciesSubmission[]>('/species-submissions', { params })
      .then((res) => res.data),

  get: (id: number) =>
    snakeClient.get<SpeciesSubmission>(`/species-submissions/${id}`).then((res) => res.data),

  create: (data: SpeciesSubmissionCreate) =>
    snakeClient.post<SpeciesSubmission>('/species-submissions', data).then((res) => res.data),

  update: (id: number, data: SpeciesSubmissionUpdate) =>
    snakeClient.patch<SpeciesSubmission>(`/species-submissions/${id}`, data).then((res) => res.data),

  remove: (id: number) => snakeClient.delete(`/species-submissions/${id}`).then((res) => res.data),

  approve: (id: number, data: SpeciesSubmissionReview) =>
    snakeClient
      .post<SpeciesSubmission>(`/species-submissions/${id}/approve`, data)
      .then((res) => res.data),

  reject: (id: number, data: SpeciesSubmissionReview) =>
    snakeClient
      .post<SpeciesSubmission>(`/species-submissions/${id}/reject`, data)
      .then((res) => res.data),
}
