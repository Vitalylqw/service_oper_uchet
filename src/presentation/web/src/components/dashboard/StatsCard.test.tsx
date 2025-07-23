import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StatsCard from './StatsCard'

describe('StatsCard', () => {
  it('renders basic stats card correctly', () => {
    render(
      <StatsCard
        title="Total Deals"
        value={42}
        subtitle="Active deals"
        icon="📄"
      />
    )

    expect(screen.getByText('Total Deals')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('Active deals')).toBeInTheDocument()
    expect(screen.getByText('📄')).toBeInTheDocument()
  })

  it('renders loading state correctly', () => {
    render(
      <StatsCard
        title="Total Deals"
        value={42}
        subtitle="Active deals"
        icon="📄"
        loading={true}
      />
    )

    expect(screen.getByText('Total Deals')).toBeInTheDocument()
    expect(screen.getByText('Загрузка...')).toBeInTheDocument()
    expect(screen.getByText('---')).toBeInTheDocument()
    expect(screen.getByText('📄')).toBeInTheDocument()
  })

  it('renders string values correctly', () => {
    render(
      <StatsCard
        title="System Status"
        value="Healthy"
        subtitle="All systems operational"
        icon="🟢"
      />
    )

    expect(screen.getByText('Healthy')).toBeInTheDocument()
    expect(screen.getByText('All systems operational')).toBeInTheDocument()
  })

  it('formats numeric values with locale formatting', () => {
    render(
      <StatsCard
        title="Total Amount"
        value={1234567}
        icon="💰"
      />
    )

    expect(screen.getByText('1,234,567')).toBeInTheDocument()
  })

  it('applies variant classes correctly', () => {
    const { container: successContainer } = render(
      <StatsCard
        title="Success"
        value="OK"
        icon="✅"
        variant="success"
      />
    )

    expect(successContainer.querySelector('.stats-card-success')).toBeInTheDocument()

    const { container: errorContainer } = render(
      <StatsCard
        title="Error"
        value="Failed"
        icon="❌"
        variant="error"
      />
    )

    expect(errorContainer.querySelector('.stats-card-error')).toBeInTheDocument()
  })

  it('renders without subtitle when not provided', () => {
    render(
      <StatsCard
        title="Simple Card"
        value={10}
        icon="📊"
      />
    )

    expect(screen.getByText('Simple Card')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('📊')).toBeInTheDocument()
    
    // Subtitle should not be present
    expect(screen.queryByTestId('stats-card-subtitle')).not.toBeInTheDocument()
  })

  it('applies loading shimmer class when loading', () => {
    const { container } = render(
      <StatsCard
        title="Loading Card"
        value={42}
        subtitle="Loading subtitle"
        icon="⏳"
        loading={true}
      />
    )

    const loadingElements = container.querySelectorAll('.loading-shimmer')
    expect(loadingElements).toHaveLength(2) // value and subtitle
  })
}) 