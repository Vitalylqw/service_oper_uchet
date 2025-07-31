import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './Dashboard'
import { dealsApi, sessionsApi } from '@/api/client'

// Mock the API clients
vi.mock('@/api/client', () => ({
  dealsApi: {
    getDealStats: vi.fn(),
    getDeals: vi.fn(),
  },
  sessionsApi: {
    getSessionStats: vi.fn(),
    getSessions: vi.fn(),
  },
}))

describe('Dashboard', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
        mutations: {
          retry: false,
        },
      },
    })

    // Mock API responses
    vi.mocked(dealsApi.getDealStats).mockResolvedValue({
      total_deals: 100,
      total_revenue: 500000,
      total_margin: 80000,
      shipped_deals: 25,
      unpaid_deals: 75,
      unshipped_deals: 75,
      unpaid_deals: 75,
      paid_deals: 25,
      avg_revenue: 5000,
      recent_changes: 5,
    })

    vi.mocked(dealsApi.getDeals).mockResolvedValue({
      items: [
        {
          id: '1',
          deal_key: 'DEAL-001',
          client_name: 'Test Client',
          saller: 'Test Seller',
          invoice_number: 'INV-001',
          invoice_date: '2024-01-01',
          revenue: '10000',
          margin: '2000',
          is_shipped: true,
          is_paid: true,
          items_count: 5,
          updated_at: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      limit: 5,
      pages: 1,
    })

    vi.mocked(sessionsApi.getSessionStats).mockResolvedValue({
      total_sessions: 50,
      successful_sessions: 45,
      failed_sessions: 5,
      last_sync_date: '2024-01-01T00:00:00Z',
    })

    vi.mocked(sessionsApi.getSessions).mockResolvedValue({
      items: [
        {
          id: '1',
          session_type: 'full',
          status: 'completed',
          started_at: '2024-01-01T00:00:00Z',
          completed_at: '2024-01-01T01:00:00Z',
          processed_count: 100,
          changed_count: 95,
          error_count: 0,
          log_messages: ['Sync completed successfully'],
        },
      ],
      total: 1,
      page: 1,
      limit: 5,
      pages: 1,
    })
  })

  const renderDashboard = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <Dashboard />
      </QueryClientProvider>
    )
  }

  it('renders dashboard header correctly', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('Панель управления')).toBeInTheDocument()
      expect(screen.getByText('Обзор системы операционного учета')).toBeInTheDocument()
    })
  })

  it('renders all stats cards', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('Всего сделок')).toBeInTheDocument()
      expect(screen.getByText('Общая выручка')).toBeInTheDocument()
      expect(screen.getByText('Не оплаченные сделки')).toBeInTheDocument()
      expect(screen.getByText('Не отгруженные сделки')).toBeInTheDocument()
      expect(screen.getByText('Итого маржа')).toBeInTheDocument()
    })
  })

  it('shows loading state initially', () => {
    renderDashboard()

    expect(screen.getByText('Загрузка данных...')).toBeInTheDocument()
  })

  it('calls all required API endpoints', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(dealsApi.getDealStats).toHaveBeenCalled()
      expect(sessionsApi.getSessionStats).toHaveBeenCalled()
      expect(dealsApi.getDeals).toHaveBeenCalledWith({ page: 1, limit: 5 })
      expect(sessionsApi.getSessions).toHaveBeenCalledWith({ page: 1, page_size: 5 })
    })
  })

  it('has correct responsive layout structure', async () => {
    const { container } = renderDashboard()

    await waitFor(() => {
      expect(container.querySelector('.dashboard')).toBeInTheDocument()
      expect(container.querySelector('.stats-grid')).toBeInTheDocument()
      expect(container.querySelector('.dashboard-content')).toBeInTheDocument()
    })
  })
}) 