import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Pagination from './Pagination'

describe('Pagination', () => {
  const mockOnPageChange = vi.fn()

  beforeEach(() => {
    mockOnPageChange.mockClear()
  })

  it('renders pagination with few pages correctly', () => {
    render(
      <Pagination
        currentPage={2}
        totalPages={5}
        onPageChange={mockOnPageChange}
      />
    )

    // Should show all pages when total pages <= 7
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()

    // Check current page is highlighted
    expect(screen.getByText('2')).toHaveClass('pagination-btn-active')
  })

  it('renders pagination with many pages and ellipsis', () => {
    render(
      <Pagination
        currentPage={5}
        totalPages={20}
        onPageChange={mockOnPageChange}
      />
    )

    // Should show first page, ellipsis, current page area, ellipsis, last page
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getAllByText('...')).toHaveLength(2)
    expect(screen.getByText('20')).toBeInTheDocument()
    expect(screen.getByText('5')).toHaveClass('pagination-btn-active')
  })

  it('calls onPageChange when page number is clicked', () => {
    render(
      <Pagination
        currentPage={2}
        totalPages={5}
        onPageChange={mockOnPageChange}
      />
    )

    fireEvent.click(screen.getByText('3'))
    expect(mockOnPageChange).toHaveBeenCalledWith(3)
  })

  it('calls onPageChange when navigation arrows are clicked', () => {
    render(
      <Pagination
        currentPage={3}
        totalPages={5}
        onPageChange={mockOnPageChange}
      />
    )

    // Test previous button
    fireEvent.click(screen.getByText('←'))
    expect(mockOnPageChange).toHaveBeenCalledWith(2)

    // Test next button
    fireEvent.click(screen.getByText('→'))
    expect(mockOnPageChange).toHaveBeenCalledWith(4)
  })

  it('disables previous button on first page', () => {
    render(
      <Pagination
        currentPage={1}
        totalPages={5}
        onPageChange={mockOnPageChange}
      />
    )

    const prevButton = screen.getByText('←')
    expect(prevButton).toBeDisabled()

    fireEvent.click(prevButton)
    expect(mockOnPageChange).not.toHaveBeenCalled()
  })

  it('disables next button on last page', () => {
    render(
      <Pagination
        currentPage={5}
        totalPages={5}
        onPageChange={mockOnPageChange}
      />
    )

    const nextButton = screen.getByText('→')
    expect(nextButton).toBeDisabled()

    fireEvent.click(nextButton)
    expect(mockOnPageChange).not.toHaveBeenCalled()
  })

  it('handles single page correctly', () => {
    render(
      <Pagination
        currentPage={1}
        totalPages={1}
        onPageChange={mockOnPageChange}
      />
    )

    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('1')).toHaveClass('pagination-btn-active')
    
    // Both navigation buttons should be disabled
    expect(screen.getByText('←')).toBeDisabled()
    expect(screen.getByText('→')).toBeDisabled()
  })

  it('shows correct pages when current page is near beginning', () => {
    render(
      <Pagination
        currentPage={2}
        totalPages={20}
        onPageChange={mockOnPageChange}
      />
    )

    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('20')).toBeInTheDocument()

    // Should only have one ellipsis (after page 3)
    expect(screen.getAllByText('...')).toHaveLength(1)
  })

  it('shows correct pages when current page is near end', () => {
    render(
      <Pagination
        currentPage={19}
        totalPages={20}
        onPageChange={mockOnPageChange}
      />
    )

    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('18')).toBeInTheDocument()
    expect(screen.getByText('19')).toBeInTheDocument()
    expect(screen.getByText('20')).toBeInTheDocument()

    // Should only have one ellipsis (before page 18)
    expect(screen.getAllByText('...')).toHaveLength(1)
  })
}) 