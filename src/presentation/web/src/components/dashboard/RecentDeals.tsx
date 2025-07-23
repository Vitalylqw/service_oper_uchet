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

  return (
    <div className="recent-deals">
      <div className="deals-list">
        {deals.map((deal) => (
          <div key={deal.id} className="deal-item">
            <div className="deal-header">
              <div className="deal-counterparty">
                <strong>{deal.counterparty_name}</strong>
                <span className="deal-inn">ИНН: {deal.inn}</span>
              </div>
              <div 
                className="deal-status"
                style={{ color: getStatusColor(deal.status) }}
              >
                {deal.status}
              </div>
            </div>
            <div className="deal-details">
              <div className="deal-contract">
                Договор №{deal.contract_number} от {formatDate(deal.contract_date)}
              </div>
              <div className="deal-amount">
                {formatAmount(deal.contract_amount)}
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