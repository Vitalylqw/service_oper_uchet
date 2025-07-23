import { useState } from 'react'

interface SessionsFiltersProps {
  filters: {
    session_type: string
    status: string
  }
  onFilterChange: (filters: Partial<{
    session_type: string
    status: string
  }>) => void
}

export default function SessionsFilters({ filters, onFilterChange }: SessionsFiltersProps) {
  const [localFilters, setLocalFilters] = useState(filters)

  const handleInputChange = (field: string, value: string) => {
    setLocalFilters((prev) => ({ ...prev, [field]: value }))
  }

  const handleApplyFilters = () => {
    onFilterChange(localFilters)
  }

  const handleResetFilters = () => {
    const resetFilters = {
      session_type: '',
      status: '',
    }
    setLocalFilters(resetFilters)
    onFilterChange(resetFilters)
  }

  const sessionTypeOptions = [
    { value: '', label: 'Все типы' },
    { value: 'full', label: 'Полная синхронизация' },
    { value: 'incremental', label: 'Инкрементальная синхронизация' },
  ]

  const statusOptions = [
    { value: '', label: 'Все статусы' },
    { value: 'running', label: 'Выполняется' },
    { value: 'completed', label: 'Завершена' },
    { value: 'failed', label: 'Ошибка' },
  ]

  return (
    <div className="sessions-filters">
      <div className="filters-header">
        <h3>Фильтры</h3>
      </div>

      <div className="filters-content">
        <div className="filter-group">
          <label htmlFor="session-type-filter">Тип синхронизации</label>
          <select
            id="session-type-filter"
            value={localFilters.session_type}
            onChange={(e) => handleInputChange('session_type', e.target.value)}
          >
            {sessionTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="status-filter">Статус</label>
          <select
            id="status-filter"
            value={localFilters.status}
            onChange={(e) => handleInputChange('status', e.target.value)}
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-actions">
          <button
            className="btn btn-primary"
            onClick={handleApplyFilters}
          >
            Применить
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleResetFilters}
          >
            Сбросить
          </button>
        </div>
      </div>
    </div>
  )
} 