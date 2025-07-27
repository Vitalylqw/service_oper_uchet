export interface Deal {
  id: string
  deal_key: string
  client_name: string
  saller: string
  invoice_number: string
  invoice_date: string
  revenue: string
  margin: string
  is_shipped: boolean
  is_paid: boolean
  items_count: number
  updated_at: string
}

export interface DealItem {
  id: string
  deal_id: string
  description: string
  quantity: number
  unit_price: number
  total_amount: number
  position: number
}

export interface SyncSession {
  id: string
  session_type: 'full' | 'incremental'
  status: 'running' | 'completed' | 'failed'
  started_at: string
  completed_at?: string
  processed_count: number
  changed_count: number
  error_count: number
  log_messages: string[]
}

export interface User {
  id: string
  username: string
  email: string
  role: 'admin' | 'analyst' | 'viewer'
  is_active: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  pages: number
}

export interface ApiError {
  detail: string
  type?: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface DealStats {
  total_deals: number
  total_amount: number
  active_deals: number
  recent_changes: number
}

export interface SessionStats {
  total_sessions: number
  successful_sessions: number
  failed_sessions: number
  last_sync_date?: string
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy'
  checks: {
    database: boolean
    redis: boolean
    file_system: boolean
  }
} 