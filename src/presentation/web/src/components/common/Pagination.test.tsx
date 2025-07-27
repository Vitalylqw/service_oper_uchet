import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Pagination from './Pagination'

describe('Pagination', () => {
  const mockOnPageChange = vi.fn()

  beforeEach(() => {
    mockOnPageChange.mockClear()
  })

  it('renders pagination controls', () => {
    render(
      <Pagination
        currentPage={1}
        totalPages={5}
        onPageChange={mockOnPageChange}
      />
    )

    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('→')).toBeInTheDocument()
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
  })

  it('calls onPageChange when next button is clicked', () => {
    render(
      <Pagination
        currentPage={1}
        totalPages={5}
        onPageChange={mockOnPageChange}
      />
    )

    const nextButton = screen.getByText('→')
    fireEvent.click(nextButton)

    expect(mockOnPageChange).toHaveBeenCalledWith(2)
  })

  it('calls onPageChange when previous button is clicked', () => {
    render(
      <Pagination
        currentPage={2}
        totalPages={5}
        onPageChange={mockOnPageChange}
      />
    )

    const prevButton = screen.getByText('←')
    fireEvent.click(prevButton)

    expect(mockOnPageChange).toHaveBeenCalledWith(1)
  })

  it('calls onPageChange when page number is clicked', () => {
    render(
      <Pagination
        currentPage={1}
        totalPages={5}
        onPageChange={mockOnPageChange}
      />
    )

    const pageButton = screen.getByText('3')
    fireEvent.click(pageButton)

    expect(mockOnPageChange).toHaveBeenCalledWith(3)
  })

  it('shows current page as active', () => {
    render(
      <Pagination
        currentPage={3}
        totalPages={5}
        onPageChange={mockOnPageChange}
      />
    )

    const currentPageButton = screen.getByText('3')
    expect(currentPageButton).toHaveClass('pagination-btn-active')
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
    // Для одной страницы стрелки должны быть отключены
    const prevButton = screen.getByText('←')
    const nextButton = screen.getByText('→')
    expect(prevButton).toBeDisabled()
    expect(nextButton).toBeDisabled()
  })

  it('shows ellipsis for large page counts', () => {
    render(
      <Pagination
        currentPage={5}
        totalPages={20}
        onPageChange={mockOnPageChange}
      />
    )

    const ellipsisElements = screen.getAllByText('...')
    expect(ellipsisElements.length).toBeGreaterThan(0)
  })
}) 