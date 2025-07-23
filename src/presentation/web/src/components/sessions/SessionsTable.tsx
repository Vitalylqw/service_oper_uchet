import type { SyncSession } from '@/types/api'
import Pagination from '../common/Pagination'

interface SessionsTableProps {
  sessions: SyncSession[]
  totalCount: number
  currentPage: number
  pageSize: number
  onPageChange: (page: number) => void
  loading: boolean
}

export default function SessionsTable({
  sessions,
  totalCount,
  currentPage,
  pageSize,
  onPageChange,
  loading,
}: SessionsTableProps) {
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

  const getDuration = (startDate: string, endDate?: string) => {
    const start = new Date(startDate)
    const end = endDate ? new Date(endDate) : new Date()
    const durationMs = end.getTime() - start.getTime()
    const minutes = Math.floor(durationMs / 60000)
    const seconds = Math.floor((durationMs % 60000) / 1000)
    return `${minutes}м ${seconds}с`
  }

  if (loading) {
    return (
      <div className="sessions-table-container">
        <div className="loading">Загрузка сессий...</div>
      </div>
    )
  }

  if (sessions.length === 0) {
    return (
      <div className="sessions-table-container">
        <div className="empty-state">
          <p>Нет сессий, соответствующих заданным критериям</p>
        </div>
      </div>
    )
  }

  const totalPages = Math.ceil(totalCount / pageSize)

  return (
    <div className="sessions-table-container">
      <div className="table-header">
        <div className="table-info">
          Найдено сессий: {totalCount}
        </div>
      </div>

      <div className="table-wrapper">
        <table className="table sessions-table">
          <thead>
            <tr>
              <th>Тип</th>
              <th>Статус</th>
              <th>Начата</th>
              <th>Длительность</th>
              <th>Обработано</th>
              <th>Изменено</th>
              <th>Ошибки</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((session) => (
              <tr key={session.id}>
                <td>
                  <div className="session-type-cell">
                    {getSessionTypeText(session.session_type)}
                  </div>
                </td>
                <td>
                  <span
                    className="status-badge"
                    style={{
                      color: getStatusColor(session.status),
                      backgroundColor: `${getStatusColor(session.status)}20`,
                    }}
                  >
                    {getStatusText(session.status)}
                  </span>
                </td>
                <td>
                  <div className="date-cell">
                    {formatDate(session.started_at)}
                  </div>
                </td>
                <td>
                  <div className="duration-cell">
                    {getDuration(session.started_at, session.completed_at)}
                  </div>
                </td>
                <td>
                  <div className="count-cell">
                    {session.processed_count.toLocaleString()}
                  </div>
                </td>
                <td>
                  <div className="count-cell">
                    {session.changed_count.toLocaleString()}
                  </div>
                </td>
                <td>
                  <div className={`count-cell ${session.error_count > 0 ? 'error-count' : ''}`}>
                    {session.error_count.toLocaleString()}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={onPageChange}
        />
      )}
    </div>
  )
} 