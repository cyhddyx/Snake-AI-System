import axios from 'axios'

export const IMAGE_SERVICE_BASE_URL = 'http://127.0.0.1:8003'

export interface UploadedImageAsset {
  filename: string
  stored_path: string
  url: string
}

const imageServiceClient = axios.create({
  baseURL: IMAGE_SERVICE_BASE_URL,
})

export interface SourceImageItem {
  relative_path: string
  url: string
}

export interface SourceImageList {
  count: number
  directory: string
  items: SourceImageItem[]
}

export const imageServiceApi = {
  upload: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    const res = await imageServiceClient.post<UploadedImageAsset>('/api/images/upload', formData)
    return res.data
  },

  health: () => imageServiceClient.get<{ status: string }>('/api/health').then((res) => res.data),

  listSourceImages: () =>
    imageServiceClient.get<SourceImageList>('/api/source-images/list').then((res) => res.data),

  importLocal: (path: string) =>
    imageServiceClient
      .post<UploadedImageAsset>('/api/images/import', { path })
      .then((res) => res.data),
}
