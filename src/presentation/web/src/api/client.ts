import axios, { AxiosError, AxiosResponse } from 'axios'
import { useAuthStore } from '@/stores/authStore'
import type {
  Deal,
  SyncSession,
  User,
  PaginatedResponse,
  LoginRequest,
  LoginResponse,
  DealStats,
  SessionStats,
  HealthStatus,
  ApiError,
} from '@/types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor to handle auth errors
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials)
    return response.data
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me')
    return response.data
  },

  getUsers: async (): Promise<User[]> => {
    const response = await apiClient.get<User[]>('/auth/users')
    return response.data
  },
}

// Deals API
export const dealsApi = {
  getDeals: async (params?: {
    page?: number
    limit?: number
    client_name?: string
    saller?: string
    is_shipped?: string
    is_paid?: string
  }): Promise<PaginatedResponse<Deal>> => {
    // Очистка пустых параметров для предотвращения ошибок валидации
    const cleanParams = {} as any
    if (params) {
      Object.keys(params).forEach(key => {
        const value = (params as any)[key]
        if (value !== undefined && value !== null && value !== '') {
          cleanParams[key] = value
        }
      })
    }
    
    const response = await apiClient.get<PaginatedResponse<Deal>>('/api/v1/deals/', {
      params: cleanParams,
    })
    return response.data
  },

  getDeal: async (dealId: string): Promise<Deal> => {
    const response = await apiClient.get<Deal>(`/api/v1/deals/${dealId}`)
    return response.data
  },

  getDealHistory: async (dealId: string): Promise<any[]> => {
    const response = await apiClient.get<any[]>(`/api/v1/deals/${dealId}/history`)
    return response.data
  },

  getDealStats: async (): Promise<DealStats> => {
    const response = await apiClient.get<DealStats>('/api/v1/deals/stats')
    return response.data
  },
}

// Sessions API
export const sessionsApi = {
  getSessions: async (params?: {
    page?: number
    page_size?: number
    session_type?: string
    status?: string
  }): Promise<PaginatedResponse<SyncSession>> => {
    const response = await apiClient.get<PaginatedResponse<SyncSession>>('/api/v1/sessions/', {
      params,
    })
    return response.data
  },

  getSession: async (sessionId: string): Promise<SyncSession> => {
    const response = await apiClient.get<SyncSession>(`/api/v1/sessions/${sessionId}`)
    return response.data
  },

  createSession: async (sessionType: 'full' | 'incremental'): Promise<SyncSession> => {
    const response = await apiClient.post<SyncSession>('/api/v1/sessions/', {
      session_type: sessionType,
    })
    return response.data
  },

  getSessionLogs: async (sessionId: string): Promise<string[]> => {
    const response = await apiClient.get<string[]>(`/api/v1/sessions/${sessionId}/logs`)
    return response.data
  },

  getSessionStats: async (): Promise<SessionStats> => {
    const response = await apiClient.get<SessionStats>('/api/v1/sessions/stats')
    return response.data
  },
}

// Health API
export const healthApi = {
  getHealth: async (): Promise<HealthStatus> => {
    const response = await apiClient.get<HealthStatus>('/health/')
    return response.data
  },

  getReadiness: async (): Promise<{ status: string }> => {
    const response = await apiClient.get<{ status: string }>('/health/ready')
    return response.data
  },

  getLiveness: async (): Promise<{ status: string }> => {
    const response = await apiClient.get<{ status: string }>('/health/live')
    return response.data
  },
} 