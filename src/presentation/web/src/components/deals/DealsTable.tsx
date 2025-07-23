import type { Deal } from '@/types/api'
import Pagination from '../common/Pagination'

interface DealsTableProps {
  deals: Deal[]
  totalCount: number
  currentPage: number
  pageSize: number
  onPageChange: (page: number) => void
  loading: boolean
}

export default function DealsTable({
  deals,
  totalCount,
  currentPage,
  pageSize,
  onPageChange,
  loading,
}: DealsTableProps) {
  const formatAmount = (amount: number) => {
    return amount.toLocaleString('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0,
    })
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
      case 'активна':
        return '#48bb78'
      case 'completed':
      case 'завершена':
        return '#4299e1'
      case 'cancelled':
      case 'отменена':
        return '#f56565'
      default:
        return '#718096'
    }
  }

  if (loading) {
    return (
      <div className="deals-table-container">
        <div className="loading">Загрузка сделок...</div>
      </div>
    )
  }

  if (deals.length === 0) {
    return (
      <div className="deals-table-container">
        <div className="empty-state">
          <p>Нет сделок, соответствующих заданным критериям</p>
        </div>
      </div>
    )
  }

  const totalPages = Math.ceil(totalCount / pageSize)

  return (
    <div className="deals-table-container">
      <div className="table-header">
        <div className="table-info">
          Найдено сделок: {totalCount}
        </div>
      </div>

      <div className="table-wrapper">
        <table className="table deals-table">
          <thead>
            <tr>
              <th>Контрагент</th>
              <th>ИНН/КПП</th>
              <th>Договор</th>
              <th>Сумма</th>
              <th>Статус</th>
              <th>Обновлена</th>
            </tr>
          </thead>
          <tbody>
            {deals.map((deal) => (
              <tr key={deal.id}>
                <td>
                  <div className="counterparty-cell">
                    <div className="counterparty-name">{deal.counterparty_name}</div>
                  </div>
                </td>
                <td>
                  <div className="inn-kpp-cell">
                    <div>ИНН: {deal.inn}</div>
                    <div className="kpp">КПП: {deal.kpp}</div>
                  </div>
                </td>
                <td>
                  <div className="contract-cell">
                    <div className="contract-number">№{deal.contract_number}</div>
                    <div className="contract-date">{formatDate(deal.contract_date)}</div>
                  </div>
                </td>
                <td>
                  <div className="amount-cell">
                    {formatAmount(deal.contract_amount)}
                  </div>
                </td>
                <td>
                  <span
                    className="status-badge"
                    style={{
                      color: getStatusColor(deal.status),
                      backgroundColor: `${getStatusColor(deal.status)}20`,
                    }}
                  >
                    {deal.status}
                  </span>
                </td>
                <td>
                  <div className="date-cell">
                    {formatDate(deal.updated_at)}
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