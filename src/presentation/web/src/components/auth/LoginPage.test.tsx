import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LoginPage from './LoginPage'
import { authApi } from '@/api/client'
import type { LoginResponse } from '@/types/api'

// Mock the auth API
vi.mock('@/api/client', () => ({
  authApi: {
    login: vi.fn(),
  },
}))

// Mock the auth store
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    login: vi.fn(),
  })),
}))

describe('LoginPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
        mutations: {
          retry: false,
        },
      },
    })
  })

  const renderLoginPage = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <LoginPage />
      </QueryClientProvider>
    )
  }

  it('renders login form', () => {
    renderLoginPage()
    
    expect(screen.getByText('Система Операционного Учета')).toBeInTheDocument()
    expect(screen.getByLabelText('Имя пользователя')).toBeInTheDocument()
    expect(screen.getByLabelText('Пароль')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Войти' })).toBeInTheDocument()
  })

  it('handles form submission', async () => {
    const mockLoginResponse: LoginResponse = {
      access_token: 'test-token',
      token_type: 'bearer',
      user: {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'viewer',
        is_active: true,
      },
    }

    vi.mocked(authApi.login).mockResolvedValue(mockLoginResponse)

    renderLoginPage()

    fireEvent.change(screen.getByLabelText('Имя пользователя'), {
      target: { value: 'testuser' },
    })
    fireEvent.change(screen.getByLabelText('Пароль'), {
      target: { value: 'password' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Войти' }))

    await waitFor(() => {
      expect(authApi.login).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password',
      })
    })
  })

  it('shows error message on login failure', async () => {
    const error = new Error('Login failed')
    vi.mocked(authApi.login).mockRejectedValue(error)

    renderLoginPage()

    fireEvent.change(screen.getByLabelText('Имя пользователя'), {
      target: { value: 'testuser' },
    })
    fireEvent.change(screen.getByLabelText('Пароль'), {
      target: { value: 'wrongpassword' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Войти' }))

    await waitFor(() => {
      expect(screen.getByText(/Ошибка входа/)).toBeInTheDocument()
    })
  })

  it('disables submit button when form is empty', () => {
    renderLoginPage()
    
    const submitButton = screen.getByRole('button', { name: 'Войти' })
    expect(submitButton).toBeDisabled()
  })

  it('enables submit button when form is filled', () => {
    renderLoginPage()
    
    fireEvent.change(screen.getByLabelText('Имя пользователя'), {
      target: { value: 'testuser' },
    })
    fireEvent.change(screen.getByLabelText('Пароль'), {
      target: { value: 'password' },
    })

    const submitButton = screen.getByRole('button', { name: 'Войти' })
    expect(submitButton).not.toBeDisabled()
  })

  it('shows demo users information', () => {
    renderLoginPage()
    
    expect(screen.getByText('Демо-пользователи:')).toBeInTheDocument()
    expect(screen.getByText(/admin/)).toBeInTheDocument()
    expect(screen.getByText(/analyst/)).toBeInTheDocument()
    expect(screen.getByText(/viewer/)).toBeInTheDocument()
  })
}) 