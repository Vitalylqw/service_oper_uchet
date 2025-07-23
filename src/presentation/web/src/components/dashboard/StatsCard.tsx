interface StatsCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: string
  loading?: boolean
  variant?: 'default' | 'success' | 'error' | 'warning'
}

export default function StatsCard({ 
  title, 
  value, 
  subtitle, 
  icon, 
  loading = false,
  variant = 'default'
}: StatsCardProps) {
  if (loading) {
    return (
      <div className="stats-card stats-card-loading">
        <div className="stats-card-icon">{icon}</div>
        <div className="stats-card-content">
          <div className="stats-card-title">{title}</div>
          <div className="stats-card-value loading-shimmer">Загрузка...</div>
          {subtitle && <div className="stats-card-subtitle loading-shimmer">---</div>}
        </div>
      </div>
    )
  }

  return (
    <div className={`stats-card stats-card-${variant}`}>
      <div className="stats-card-icon">{icon}</div>
      <div className="stats-card-content">
        <div className="stats-card-title">{title}</div>
        <div className="stats-card-value">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
        {subtitle && <div className="stats-card-subtitle">{subtitle}</div>}
      </div>
    </div>
  )
} 