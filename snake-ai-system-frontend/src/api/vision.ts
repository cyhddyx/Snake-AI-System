import axios from 'axios'
export interface Candidate {
  // 根据你后端 predictor.predict 返回的实际结构定义
  rank: number
  species: string
  confidence: number
}
export interface PredictResponse {
  status: string
  candidates: Candidate[]
}
export async function predictCandidates(file: File): Promise<PredictResponse> {
  const formData = new FormData()
  formData.append('file', file)  // key 必须是 'file'，和后端参数名一致
  const { data } = await axios.post<PredictResponse>(
    'http://localhost:8000/predict_candidates',
    formData
  )
  return data
}
