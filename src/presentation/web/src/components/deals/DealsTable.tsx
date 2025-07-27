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
  const formatAmount = (amount: string) => {
    const numAmount = parseFloat(amount)
    return numAmount.toLocaleString('ru-RU', {
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

  const formatBoolean = (value: boolean) => {
    return value ? 'Да' : 'Нет'
  }

  const getBooleanColor = (value: boolean) => {
    return value ? '#48bb78' : '#ed8936' // green for true, orange for false
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
               <th>Клиент</th>
               <th>Продавец</th>
               <th>Счет</th>
               <th>Доход/Маржа</th>
               <th>Отгружено</th>
               <th>Оплачено</th>
               <th>Обновлена</th>
             </tr>
           </thead>
                     <tbody>
             {deals.map((deal) => (
               <tr key={deal.id}>
                 <td>
                   <div className="client-cell">
                     <div className="client-name">{deal.client_name}</div>
                   </div>
                 </td>
                 <td>
                   <div className="saller-cell">
                     <div className="saller-name">{deal.saller}</div>
                   </div>
                 </td>
                 <td>
                   <div className="invoice-cell">
                     <div className="invoice-number">№{deal.invoice_number}</div>
                     <div className="invoice-date">{formatDate(deal.invoice_date)}</div>
                   </div>
                 </td>
                 <td>
                   <div className="financial-cell">
                     <div className="revenue">Доход: {formatAmount(deal.revenue)}</div>
                     <div className="margin">Маржа: {formatAmount(deal.margin)}</div>
                   </div>
                 </td>
                                   <td>
                    <span
                      className="status-badge"
                      style={{
                        color: getBooleanColor(deal.is_shipped),
                        backgroundColor: `${getBooleanColor(deal.is_shipped)}20`,
                      }}
                    >
                      {formatBoolean(deal.is_shipped)}
                    </span>
                  </td>
                  <td>
                    <span
                      className="status-badge"
                      style={{
                        color: getBooleanColor(deal.is_paid),
                        backgroundColor: `${getBooleanColor(deal.is_paid)}20`,
                      }}
                    >
                      {formatBoolean(deal.is_paid)}
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