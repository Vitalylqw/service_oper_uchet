import { useState } from 'react'

interface DealsFiltersProps {
  filters: {
    inn: string
    counterparty_name: string
    status: string
  }
  onFilterChange: (filters: Partial<{
    inn: string
    counterparty_name: string
    status: string
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
      inn: '',
      counterparty_name: '',
      status: '',
    }
    setLocalFilters(resetFilters)
    onFilterChange(resetFilters)
  }

  const statusOptions = [
    { value: '', label: 'Все статусы' },
    { value: 'active', label: 'Активные' },
    { value: 'completed', label: 'Завершенные' },
    { value: 'cancelled', label: 'Отмененные' },
  ]

  return (
    <div className="deals-filters">
      <div className="filters-header">
        <h3>Фильтры</h3>
      </div>

      <div className="filters-content">
        <div className="filter-group">
          <label htmlFor="inn-filter">ИНН</label>
          <input
            type="text"
            id="inn-filter"
            value={localFilters.inn}
            onChange={(e) => handleInputChange('inn', e.target.value)}
            placeholder="Введите ИНН"
          />
        </div>

        <div className="filter-group">
          <label htmlFor="counterparty-filter">Контрагент</label>
          <input
            type="text"
            id="counterparty-filter"
            value={localFilters.counterparty_name}
            onChange={(e) => handleInputChange('counterparty_name', e.target.value)}
            placeholder="Название контрагента"
          />
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