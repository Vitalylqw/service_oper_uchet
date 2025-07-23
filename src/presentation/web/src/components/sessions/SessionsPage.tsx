import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sessionsApi } from '@/api/client'
import { useAuthStore } from '@/stores/authStore'
import type { SyncSession } from '@/types/api'
import SessionsTable from './SessionsTable'
import SessionsFilters from './SessionsFilters'
import './SessionsPage.css'

export default function SessionsPage() {
  const { user } = useAuthStore()
  const queryClient = useQueryClient()
  
  const [filters, setFilters] = useState({
    page: 1,
    page_size: 20,
    session_type: '',
    status: '',
  })

  const { data: sessionsData, isLoading, error } = useQuery({
    queryKey: ['sessions', filters],
    queryFn: () => sessionsApi.getSessions(filters),
  })

  const createSessionMutation = useMutation({
    mutationFn: sessionsApi.createSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })

  const handleFilterChange = (newFilters: Partial<typeof filters>) => {
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
      page: 1,
    }))
  }

  const handlePageChange = (page: number) => {
    setFilters((prev) => ({ ...prev, page }))
  }

  const handleCreateSession = (sessionType: 'full' | 'incremental') => {
    createSessionMutation.mutate(sessionType)
  }

  const canCreateSession = user?.role === 'admin' || user?.role === 'analyst'

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
        <div className="header-content">
          <h2>Сессии синхронизации</h2>
          <p>Управление и мониторинг процессов синхронизации данных</p>
        </div>
        
        {canCreateSession && (
          <div className="header-actions">
            <button
              className="btn btn-secondary"
              onClick={() => handleCreateSession('incremental')}
              disabled={createSessionMutation.isPending}
            >
              Инкрементальная синхронизация
            </button>
            <button
              className="btn btn-primary"
              onClick={() => handleCreateSession('full')}
              disabled={createSessionMutation.isPending}
            >
              Полная синхронизация
            </button>
          </div>
        )}
      </div>

      {createSessionMutation.error && (
        <div className="error">
          Ошибка создания сессии: {(createSessionMutation.error as any)?.response?.data?.detail || 'Неизвестная ошибка'}
        </div>
      )}

      <div className="page-content">
        <SessionsFilters
          filters={filters}
          onFilterChange={handleFilterChange}
        />

        <SessionsTable
          sessions={sessionsData?.items || []}
          totalCount={sessionsData?.total || 0}
          currentPage={filters.page}
          pageSize={filters.page_size}
          onPageChange={handlePageChange}
          loading={isLoading}
        />
      </div>
    </div>
  )
} 