import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dealsApi } from '@/api/client'
import type { Deal } from '@/types/api'
import DealsTable from './DealsTable'
import DealsFilters from './DealsFilters'
import './DealsPage.css'

export default function DealsPage() {
  const [filters, setFilters] = useState({
    page: 1,
    page_size: 20,
    inn: '',
    counterparty_name: '',
    status: '',
  })

  const { data: dealsData, isLoading, error } = useQuery({
    queryKey: ['deals', filters],
    queryFn: () => dealsApi.getDeals(filters),
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
      <div className="deals-page">
        <div className="error">
          Ошибка загрузки сделок: {(error as any)?.response?.data?.detail || 'Неизвестная ошибка'}
        </div>
      </div>
    )
  }

  return (
    <div className="deals-page">
      <div className="page-header">
        <h2>Сделки</h2>
        <p>Управление и просмотр всех сделок в системе</p>
      </div>

      <div className="page-content">
        <DealsFilters
          filters={filters}
          onFilterChange={handleFilterChange}
        />

        <DealsTable
          deals={dealsData?.items || []}
          totalCount={dealsData?.total || 0}
          currentPage={filters.page}
          pageSize={filters.page_size}
          onPageChange={handlePageChange}
          loading={isLoading}
        />
      </div>
    </div>
  )
} 