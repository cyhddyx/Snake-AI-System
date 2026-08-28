import axios from 'axios'

const BASE_URL = 'http://127.0.0.1:8002'
let authToken = ''

export const setAuthToken = (token: string) => {
  authToken = token
}

export const snakeClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

snakeClient.interceptors.request.use((config) => {
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`
  } else if (config.headers?.Authorization) {
    delete config.headers.Authorization
  }
  return config
})

export const SNAKE_API = BASE_URL
