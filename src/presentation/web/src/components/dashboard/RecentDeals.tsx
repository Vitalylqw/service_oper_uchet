import type { Deal } from '@/types/api'

interface RecentDealsProps {
  deals: Deal[]
  loading: boolean
}

export default function RecentDeals({ deals, loading }: RecentDealsProps) {
  if (loading) {
    return (
      <div className="recent-deals">
        <div className="loading">Загрузка сделок...</div>
      </div>
    )
  }

  if (deals.length === 0) {
    return (
      <div className="recent-deals">
        <div className="empty-state">
          <p>Нет данных о сделках</p>
        </div>
      </div>
    )
  }

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

  const getStatus = (isShipped: boolean, isPaid: boolean) => {
    if (isShipped && isPaid) return 'Завершена'
    if (isShipped && !isPaid) return 'Отгружена'
    if (!isShipped && isPaid) return 'Оплачена'
    return 'Активна'
  }

  const getStatusColor = (isShipped: boolean, isPaid: boolean) => {
    if (isShipped && isPaid) return '#4299e1' // blue - completed
    if (isShipped && !isPaid) return '#ed8936' // orange - shipped
    if (!isShipped && isPaid) return '#38b2ac' // teal - paid
    return '#48bb78' // green - active
  }

  return (
    <div className="recent-deals">
      <div className="section-header">
        <h3>Последние сделки</h3>
        <a href="/deals" className="view-all-link">Все сделки</a>
      </div>
      <div className="deals-list">
        {deals.map((deal) => (
          <div key={deal.id} className="deal-item">
            <div className="deal-header">
              <div className="deal-counterparty">
                <strong>{deal.client_name}</strong>
                <span className="deal-saller">Продавец: {deal.saller}</span>
              </div>
              <div 
                className="deal-status"
                style={{ color: getStatusColor(deal.is_shipped, deal.is_paid) }}
              >
                {getStatus(deal.is_shipped, deal.is_paid)}
              </div>
            </div>
            <div className="deal-details">
              <div className="deal-contract">
                Счет №{deal.invoice_number} от {formatDate(deal.invoice_date)}
              </div>
              <div className="deal-amount">
                {formatAmount(deal.revenue)}
              </div>
            </div>
            <div className="deal-footer">
              <span className="deal-updated">
                Обновлена: {formatDate(deal.updated_at)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
} 