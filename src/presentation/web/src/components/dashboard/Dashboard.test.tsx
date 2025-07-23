import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './Dashboard'

// Mock the API modules
vi.mock('@/api/client', () => ({
  dealsApi: {
    getDealStats: vi.fn(),
    getDeals: vi.fn(),
  },
  sessionsApi: {
    getSessionStats: vi.fn(),
    getSessions: vi.fn(),
  },
  healthApi: {
    getHealth: vi.fn(),
  },
}))

// Mock child components
vi.mock('./StatsCard', () => ({
  default: ({ title, value, loading }: any) => (
    <div data-testid="stats-card">
      <div>{title}</div>
      <div>{loading ? 'Loading...' : value}</div>
    </div>
  ),
}))

vi.mock('./RecentDeals', () => ({
  default: ({ deals, loading }: any) => (
    <div data-testid="recent-deals">
      {loading ? 'Loading deals...' : `${deals.length} deals`}
    </div>
  ),
}))

vi.mock('./SessionStatus', () => ({
  default: ({ sessions, loading }: any) => (
    <div data-testid="session-status">
      {loading ? 'Loading sessions...' : `${sessions.length} sessions`}
    </div>
  ),
}))

describe('Dashboard', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    
    vi.clearAllMocks()
  })

  const renderDashboard = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <Dashboard />
      </QueryClientProvider>
    )
  }

  it('renders dashboard header correctly', () => {
    renderDashboard()

    expect(screen.getByText('Обзор системы')).toBeInTheDocument()
    expect(screen.getByText('Текущий статус и основные метрики системы операционного учета')).toBeInTheDocument()
  })

  it('renders all stats cards', () => {
    renderDashboard()

    const statsCards = screen.getAllByTestId('stats-card')
    expect(statsCards).toHaveLength(4)

    // Check that the cards contain expected titles
    expect(screen.getByText('Всего сделок')).toBeInTheDocument()
    expect(screen.getByText('Активные сделки')).toBeInTheDocument()
    expect(screen.getByText('Недавние изменения')).toBeInTheDocument()
    expect(screen.getByText('Статус системы')).toBeInTheDocument()
  })

  it('renders recent deals and session status sections', () => {
    renderDashboard()

    expect(screen.getByText('Последние сделки')).toBeInTheDocument()
    expect(screen.getByText('Статус синхронизации')).toBeInTheDocument()
    
    expect(screen.getByTestId('recent-deals')).toBeInTheDocument()
    expect(screen.getByTestId('session-status')).toBeInTheDocument()
  })

  it('renders navigation links correctly', () => {
    renderDashboard()

    const viewAllLinks = screen.getAllByText(/→/)
    expect(viewAllLinks).toHaveLength(2)

    // Check specific link texts
    expect(screen.getByText('Все сделки →')).toBeInTheDocument()
    expect(screen.getByText('Все сессии →')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    renderDashboard()

    // All stats cards should show loading initially
    const loadingTexts = screen.getAllByText('Loading...')
    expect(loadingTexts.length).toBeGreaterThan(0)

    expect(screen.getByText('Loading deals...')).toBeInTheDocument()
    expect(screen.getByText('Loading sessions...')).toBeInTheDocument()
  })

  it('calls all required API endpoints', async () => {
    const { dealsApi, sessionsApi, healthApi } = await import('@/api/client')

    renderDashboard()

    expect(dealsApi.getDealStats).toHaveBeenCalled()
    expect(sessionsApi.getSessionStats).toHaveBeenCalled()
    expect(healthApi.getHealth).toHaveBeenCalled()
    expect(dealsApi.getDeals).toHaveBeenCalledWith({ page: 1, page_size: 5 })
    expect(sessionsApi.getSessions).toHaveBeenCalledWith({ page: 1, page_size: 3 })
  })

  it('has correct responsive layout structure', () => {
    const { container } = renderDashboard()

    expect(container.querySelector('.dashboard')).toBeInTheDocument()
    expect(container.querySelector('.stats-grid')).toBeInTheDocument()
    expect(container.querySelector('.dashboard-content')).toBeInTheDocument()
  })
}) 