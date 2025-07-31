interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: string;
  loading?: boolean;
  variant?: 'default' | 'success' | 'error' | 'warning';
  format?: 'currency' | 'number' | 'percent';
}

const formatValue = (
  value: string | number,
  format: 'currency' | 'number' | 'percent' = 'number',
): string => {
  const numericValue = typeof value === 'string' ? parseFloat(value) : value;

  if (isNaN(numericValue)) {
    return String(value); // Fallback for non-numeric strings
  }

  const options: Intl.NumberFormatOptions = {
    style: 'decimal',
    maximumFractionDigits: 2,
    useGrouping: true,
  };

  if (format === 'percent') {
    options.maximumFractionDigits = 2;
    return new Intl.NumberFormat('ru-RU', options).format(numericValue) + ' %';
  }

  if (format === 'currency') {
    options.style = 'currency';
    options.currency = 'RUB';
    options.minimumFractionDigits = 2;
  } else {
    if (Number.isInteger(numericValue)) {
      options.maximumFractionDigits = 0;
    }
  }

  return new Intl.NumberFormat('ru-RU', options).format(numericValue);
};


export default function StatsCard({
  title,
  value,
  subtitle,
  icon,
  loading = false,
  variant = 'default',
  format = 'number',
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
    );
  }

  return (
    <div className={`stats-card stats-card-${variant}`}>
      <div className="stats-card-icon">{icon}</div>
      <div className="stats-card-content">
        <div className="stats-card-title">{title}</div>
        <div className="stats-card-value">{formatValue(value, format)}</div>
        {subtitle && <div className="stats-card-subtitle">{subtitle}</div>}
      </div>
    </div>
  );
}
