import type { SyncSession, SessionStats } from '@/types/api'

interface SessionStatusProps {
  sessions: SyncSession[]
  stats?: SessionStats
  loading: boolean
}

export default function SessionStatus({ sessions, stats, loading }: SessionStatusProps) {
  if (loading) {
    return (
      <div className="session-status">
        <div className="loading">Загрузка данных синхронизации...</div>
      </div>
    )
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return '#48bb78'
      case 'running':
        return '#4299e1'
      case 'failed':
        return '#f56565'
      default:
        return '#718096'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Завершена'
      case 'running':
        return 'Выполняется'
      case 'failed':
        return 'Ошибка'
      default:
        return status
    }
  }

  const getSessionTypeText = (type: string) => {
    switch (type) {
      case 'full':
        return 'Полная'
      case 'incremental':
        return 'Инкрементальная'
      default:
        return type
    }
  }

  return (
    <div className="session-status">
      {stats && (
        <div className="session-stats">
          <div className="stat-item">
            <span className="stat-label">Всего сессий:</span>
            <span className="stat-value">{stats.total_sessions}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Успешных:</span>
            <span className="stat-value success">{stats.successful_sessions}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">С ошибками:</span>
            <span className="stat-value error">{stats.failed_sessions}</span>
          </div>
          {stats.last_sync_date && (
            <div className="stat-item">
              <span className="stat-label">Последняя:</span>
              <span className="stat-value">{formatDate(stats.last_sync_date)}</span>
            </div>
          )}
        </div>
      )}

      <div className="session-list">
        {sessions.length === 0 ? (
          <div className="empty-state">
            <p>Нет данных о сессиях синхронизации</p>
          </div>
        ) : (
          sessions.map((session) => (
            <div key={session.id} className="session-item">
              <div className="session-header">
                <div className="session-type">
                  {getSessionTypeText(session.session_type)}
                </div>
                <div 
                  className="session-status-badge"
                  style={{ color: getStatusColor(session.status) }}
                >
                  {getStatusText(session.status)}
                </div>
              </div>
              <div className="session-details">
                <div className="session-time">
                  Начата: {formatDate(session.started_at)}
                  {session.completed_at && (
                    <span> • Завершена: {formatDate(session.completed_at)}</span>
                  )}
                </div>
                <div className="session-counts">
                  <span>Обработано: {session.processed_count}</span>
                  <span>Изменено: {session.changed_count}</span>
                  {session.error_count > 0 && (
                    <span className="error-count">Ошибок: {session.error_count}</span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
} 