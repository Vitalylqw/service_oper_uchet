import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dealsApi } from '@/api/client'
import DealsTable from './DealsTable'
import DealsFilters from './DealsFilters'
import './DealsPage.css'

export default function DealsPage() {
  const [filters, setFilters] = useState({
    page: 1,
    limit: 20,
    client_name: '',
    saller: '',
    is_shipped: '',
    is_paid: '',
  })

  // Очистка пустых фильтров для корректного cache key
  const cleanFilters = Object.fromEntries(
    Object.entries(filters).filter(([, value]) => 
      value !== undefined && value !== null && value !== ''
    )
  )

  const { data: dealsData, isLoading, error } = useQuery({
    queryKey: ['deals', cleanFilters],
    queryFn: () => dealsApi.getDeals(cleanFilters),
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
          pageSize={filters.limit}
          onPageChange={handlePageChange}
          loading={isLoading}
        />
      </div>
    </div>
  )
} 