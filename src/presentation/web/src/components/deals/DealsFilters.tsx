import { useState } from 'react'

interface DealsFiltersProps {
  filters: {
    client_name: string
    saller: string
    is_shipped: string
    is_paid: string
  }
  onFilterChange: (filters: Partial<{
    client_name: string
    saller: string
    is_shipped: string
    is_paid: string
  }>) => void
}

export default function DealsFilters({ filters, onFilterChange }: DealsFiltersProps) {
  const [localFilters, setLocalFilters] = useState(filters)

  const handleInputChange = (field: string, value: string) => {
    setLocalFilters((prev) => ({ ...prev, [field]: value }))
  }

  const handleApplyFilters = () => {
    onFilterChange(localFilters)
  }

  const handleResetFilters = () => {
    const resetFilters = {
      client_name: '',
      saller: '',
      is_shipped: '',
      is_paid: '',
    }
    setLocalFilters(resetFilters)
    onFilterChange(resetFilters)
  }

  const booleanOptions = [
    { value: '', label: 'Все' },
    { value: 'true', label: 'Да' },
    { value: 'false', label: 'Нет' },
  ]

  return (
    <div className="deals-filters">
      <div className="filters-header">
        <h3>Фильтры</h3>
      </div>

      <div className="filters-content">
        <div className="filter-group">
          <label htmlFor="client-filter">Клиент</label>
          <input
            type="text"
            id="client-filter"
            value={localFilters.client_name}
            onChange={(e) => handleInputChange('client_name', e.target.value)}
            placeholder="Название клиента"
          />
        </div>

        <div className="filter-group">
          <label htmlFor="saller-filter">Продавец</label>
          <input
            type="text"
            id="saller-filter"
            value={localFilters.saller}
            onChange={(e) => handleInputChange('saller', e.target.value)}
            placeholder="Имя продавца"
          />
        </div>

        <div className="filter-group">
          <label htmlFor="shipped-filter">Отгружено</label>
          <select
            id="shipped-filter"
            value={localFilters.is_shipped}
            onChange={(e) => handleInputChange('is_shipped', e.target.value)}
          >
            {booleanOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="paid-filter">Оплачено</label>
          <select
            id="paid-filter"
            value={localFilters.is_paid}
            onChange={(e) => handleInputChange('is_paid', e.target.value)}
          >
            {booleanOptions.map((option) => (
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