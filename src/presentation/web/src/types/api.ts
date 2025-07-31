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
  period_month?: string | null
  period_year?: string | null
  period_full_name?: string | null
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
  finished_at?: string  // API возвращает finished_at, а не completed_at
  duration_seconds?: number
  total_deals_processed: number
  success: boolean
  error_message?: string
  processed_count: number
  changed_count: number
  error_count: number
  log_messages?: string[]  // Опционально, так как API может не возвращать
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
  total_revenue: number      // общая выручка
  total_margin: number       // итоговая маржа
  shipped_deals?: number     // отгруженные
  paid_deals?: number        // оплаченные
  avg_revenue?: number       // средняя выручка
  avg_profitability?: number   // средняя рентабельность, %
  unpaid_deals?: number       // не оплачено
  unshipped_deals?: number    // не отгружено
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