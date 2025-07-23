import { useQuery } from '@tanstack/react-query'
import { dealsApi, sessionsApi, healthApi } from '@/api/client'
import StatsCard from './StatsCard'
import RecentDeals from './RecentDeals'
import SessionStatus from './SessionStatus'
import './Dashboard.css'

export default function Dashboard() {
  const { data: dealStats, isLoading: dealStatsLoading } = useQuery({
    queryKey: ['dealStats'],
    queryFn: dealsApi.getDealStats,
  })

  const { data: sessionStats, isLoading: sessionStatsLoading } = useQuery({
    queryKey: ['sessionStats'],
    queryFn: sessionsApi.getSessionStats,
  })

  const { data: healthStatus, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: healthApi.getHealth,
    refetchInterval: 30000, // Обновлять каждые 30 секунд
  })

  const { data: recentDeals, isLoading: recentDealsLoading } = useQuery({
    queryKey: ['recentDeals'],
    queryFn: () => dealsApi.getDeals({ page: 1, page_size: 5 }),
  })

  const { data: recentSessions, isLoading: recentSessionsLoading } = useQuery({
    queryKey: ['recentSessions'],
    queryFn: () => sessionsApi.getSessions({ page: 1, page_size: 3 }),
  })

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Обзор системы</h2>
        <p>Текущий статус и основные метрики системы операционного учета</p>
      </div>

      <div className="stats-grid">
        <StatsCard
          title="Всего сделок"
          value={dealStats?.total_deals || 0}
          subtitle={`На сумму ${dealStats?.total_amount?.toLocaleString() || 0} ₽`}
          icon="📄"
          loading={dealStatsLoading}
        />
        <StatsCard
          title="Активные сделки"
          value={dealStats?.active_deals || 0}
          subtitle="В работе"
          icon="✅"
          loading={dealStatsLoading}
        />
        <StatsCard
          title="Недавние изменения"
          value={dealStats?.recent_changes || 0}
          subtitle="За последние 24 часа"
          icon="🔄"
          loading={dealStatsLoading}
        />
        <StatsCard
          title="Статус системы"
          value={healthStatus?.status === 'healthy' ? 'Работает' : 'Проблемы'}
          subtitle={`БД: ${healthStatus?.checks?.database ? '✅' : '❌'} Redis: ${healthStatus?.checks?.redis ? '✅' : '❌'}`}
          icon="🖥️"
          loading={healthLoading}
          variant={healthStatus?.status === 'healthy' ? 'success' : 'error'}
        />
      </div>

      <div className="dashboard-content">
        <div className="dashboard-section">
          <div className="section-header">
            <h3>Последние сделки</h3>
            <a href="/deals" className="view-all-link">Все сделки →</a>
          </div>
          <RecentDeals deals={recentDeals?.items || []} loading={recentDealsLoading} />
        </div>

        <div className="dashboard-section">
          <div className="section-header">
            <h3>Статус синхронизации</h3>
            <a href="/sessions" className="view-all-link">Все сессии →</a>
          </div>
          <SessionStatus 
            sessions={recentSessions?.items || []} 
            stats={sessionStats}
            loading={recentSessionsLoading || sessionStatsLoading} 
          />
        </div>
      </div>
    </div>
  )
} 