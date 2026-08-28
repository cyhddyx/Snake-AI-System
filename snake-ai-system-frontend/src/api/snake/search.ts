import { snakeClient } from '../snake'
import type { Species } from './species'
import type { Family } from './families'
import type { Genus } from './genera'

export interface SearchResult {
  species: Species[]
  families: Family[]
  genera: Genus[]
}

export interface SearchTotal {
  species: number
  families: number
  genera: number
}

export interface SearchResponse {
  results: SearchResult
  total: SearchTotal
}

export interface SearchParams {
  q: string
  searchType?: 'species' | 'family' | 'genus' | 'all'
  toxicity?: string
  iucnStatus?: string
  familyId?: number
  genusId?: number
  limit?: number
  offset?: number
}

export const searchApi = {
  search: (params: SearchParams) => {
    const queryParams: Record<string, any> = {
      q: params.q,
      search_type: params.searchType || 'all',
    }
    if (params.toxicity) queryParams.toxicity = params.toxicity
    if (params.iucnStatus) queryParams.iucn_status = params.iucnStatus
    if (params.familyId) queryParams.family_id = params.familyId
    if (params.genusId) queryParams.genus_id = params.genusId
    if (params.limit) queryParams.limit = params.limit
    if (params.offset) queryParams.offset = params.offset

    return snakeClient
      .get<SearchResponse>('/search', { params: queryParams })
      .then((res) => res.data)
  },

  initFulltext: () =>
    snakeClient.post<{ message: string }>('/search/init-fulltext').then((res) => res.data),
}
