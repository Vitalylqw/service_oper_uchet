import { useQuery } from '@tanstack/react-query'
import { dealsApi, sessionsApi } from '@/api/client'
import StatsCard from './StatsCard'
import RecentDeals from './RecentDeals'
import SessionStatus from './SessionStatus'
import './Dashboard.css'

export default function Dashboard() {
  // Получаем статистику по сделкам
  const { data: dealStats, isLoading: dealsLoading } = useQuery({
    queryKey: ['dealStats'],
    queryFn: () => dealsApi.getDealStats(),
  })

  // Получаем последние сделки
  const { data: recentDeals, isLoading: dealsListLoading } = useQuery({
    queryKey: ['recentDeals'],
    queryFn: () => dealsApi.getDeals({ page: 1, limit: 5 }),
  })

  // Получаем статистику по сессиям
  const { data: sessionStats, isLoading: sessionsLoading } = useQuery({
    queryKey: ['sessionStats'],
    queryFn: () => sessionsApi.getSessionStats(),
  })

  // Получаем последние сессии
  const { data: recentSessions, isLoading: sessionsListLoading } = useQuery({
    queryKey: ['recentSessions'],
    queryFn: () => sessionsApi.getSessions({ page: 1, page_size: 5 }),
  })

  const isLoading = dealsLoading || dealsListLoading || sessionsLoading || sessionsListLoading

  if (isLoading) {
    return (
      <div className="dashboard">
        <div className="dashboard-header">
          <h1>Панель управления</h1>
          <p>Обзор системы операционного учета</p>
        </div>
        <div className="loading">Загрузка данных...</div>
      </div>
    )
  }

  const unpaidDeals = dealStats?.unpaid_deals ?? 0
  const unshippedDeals = dealStats?.unshipped_deals ?? 0

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Панель управления</h1>
        <p>Обзор системы операционного учета</p>
      </div>

      <div className="dashboard-content">
        {/* Статистические карточки */}
        <div className="stats-grid">
          <StatsCard
            title="Всего сделок"
            value={dealStats?.total_deals || 0}
            icon="📊"
            format="number"
          />
          <StatsCard
            title="Не оплаченные сделки"
            value={unpaidDeals}
            icon="💳"
            format="number"
          />
          <StatsCard
            title="Не отгруженные сделки"
            value={unshippedDeals}
            icon="🚚"
            format="number"
          />
          <StatsCard
            title="Общая выручка"
            value={dealStats?.total_revenue ?? 0}
            icon="💰"
            format="currency"
          />
          <StatsCard
            title="Итого маржа"
            value={dealStats?.total_margin ?? 0}
            icon="📈"
            format="currency"
          />
          <StatsCard
            title="Рентабельность"
            value={dealStats?.avg_profitability ?? 0}
            icon="💹"
            format="percent"
          />
        </div>

        {/* Основной контент */}
        <div className="dashboard-main">
          <div className="dashboard-section">
            <RecentDeals 
              deals={recentDeals?.items || []} 
              loading={dealsListLoading}
            />
          </div>

          <div className="dashboard-section">
            <SessionStatus 
              sessions={recentSessions?.items || []}
              stats={sessionStats}
              loading={sessionsListLoading || sessionsLoading}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
