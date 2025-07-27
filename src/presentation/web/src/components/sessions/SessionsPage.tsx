import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { sessionsApi } from '@/api/client'
import SessionsTable from './SessionsTable'
import SessionsFilters from './SessionsFilters'
import './SessionsPage.css'

export default function SessionsPage() {
  const [filters, setFilters] = useState({
    page: 1,
    limit: 20,
    session_type: '',
    status: '',
  })

  const { data: sessionsData, isLoading, error } = useQuery({
    queryKey: ['sessions', filters],
    queryFn: () => sessionsApi.getSessions(filters),
  })

  const handleFilterChange = (newFilters: Partial<typeof filters>) => {
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
      page: 1, // Сброс на первую страницу при изменении фильтров
    }))
  }

  const handlePageChange = (page: number) => {
    setFilters((prev) => ({ ...prev, page }))
  }

  if (error) {
    return (
      <div className="sessions-page">
        <div className="error">
          Ошибка загрузки сессий: {(error as any)?.response?.data?.detail || 'Неизвестная ошибка'}
        </div>
      </div>
    )
  }

  return (
    <div className="sessions-page">
      <div className="page-header">
        <h2>Сессии синхронизации</h2>
        <p>Управление и мониторинг сессий синхронизации данных</p>
      </div>

      <div className="page-content">
        <SessionsFilters
          filters={filters}
          onFilterChange={handleFilterChange}
        />

        <SessionsTable
          sessions={sessionsData?.items || []}
          totalCount={sessionsData?.total || 0}
          currentPage={filters.page}
          pageSize={filters.limit}
          onPageChange={handlePageChange}
          loading={isLoading}
        />
      </div>
    </div>
  )
} 