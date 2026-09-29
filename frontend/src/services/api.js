import axios from 'axios'

// In local development (two separate dev servers), default to the backend
// running on :8000. In a production build with no VITE_API_URL set, default
// to '' (a relative/same-origin base) -- this is what makes the merged
// single-service deployment (backend serving the built frontend) work with
// zero environment variables and zero CORS requests.
const BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000')

export const api = axios.create({ baseURL: BASE_URL })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('fg_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const adminApi = axios.create({ baseURL: BASE_URL })

adminApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('fg_admin_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export function apiErrorMessage(err, fallback = 'Something went wrong. Please try again.') {
  return err?.response?.data?.detail || fallback
}