import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LoginPage from './LoginPage'
import { useAuthStore } from '@/stores/authStore'

// Mock the auth store
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(),
}))

// Mock the API client
vi.mock('@/api/client', () => ({
  authApi: {
    login: vi.fn(),
  },
}))

const mockLogin = vi.fn()

describe('LoginPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    
    vi.mocked(useAuthStore).mockReturnValue({
      user: null,
      token: null,
      isAuthenticated: false,
      login: mockLogin,
      logout: vi.fn(),
      updateUser: vi.fn(),
    })
    
    mockLogin.mockClear()
  })

  const renderLoginPage = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <LoginPage />
      </QueryClientProvider>
    )
  }

  it('renders login form correctly', () => {
    renderLoginPage()

    expect(screen.getByText('Система Операционного Учета')).toBeInTheDocument()
    expect(screen.getByText('Войдите в систему для продолжения')).toBeInTheDocument()
    expect(screen.getByLabelText('Имя пользователя')).toBeInTheDocument()
    expect(screen.getByLabelText('Пароль')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Войти' })).toBeInTheDocument()
  })

  it('shows demo users information', () => {
    renderLoginPage()

    expect(screen.getByText('Демо-пользователи:')).toBeInTheDocument()
    expect(screen.getByText('admin')).toBeInTheDocument()
    expect(screen.getByText('/ password (Администратор)')).toBeInTheDocument()
    expect(screen.getByText('analyst')).toBeInTheDocument()
    expect(screen.getByText('/ password (Аналитик)')).toBeInTheDocument()
    expect(screen.getByText('viewer')).toBeInTheDocument()
    expect(screen.getByText('/ password (Наблюдатель)')).toBeInTheDocument()
  })

  it('enables submit button only when both fields are filled', () => {
    renderLoginPage()

    const submitButton = screen.getByRole('button', { name: 'Войти' })
    const usernameInput = screen.getByLabelText('Имя пользователя')
    const passwordInput = screen.getByLabelText('Пароль')

    // Initially disabled
    expect(submitButton).toBeDisabled()

    // Fill username only
    fireEvent.change(usernameInput, { target: { value: 'admin' } })
    expect(submitButton).toBeDisabled()

    // Fill password only
    fireEvent.change(usernameInput, { target: { value: '' } })
    fireEvent.change(passwordInput, { target: { value: 'password' } })
    expect(submitButton).toBeDisabled()

    // Fill both fields
    fireEvent.change(usernameInput, { target: { value: 'admin' } })
    expect(submitButton).toBeEnabled()
  })

  it('updates form state when user types', () => {
    renderLoginPage()

    const usernameInput = screen.getByLabelText('Имя пользователя')
    const passwordInput = screen.getByLabelText('Пароль')

    fireEvent.change(usernameInput, { target: { value: 'testuser' } })
    fireEvent.change(passwordInput, { target: { value: 'testpass' } })

    expect(usernameInput).toHaveValue('testuser')
    expect(passwordInput).toHaveValue('testpass')
  })

  it('shows loading state when form is submitted', async () => {
    const { authApi } = await import('@/api/client')
    
    // Mock API to return a pending promise
    const pendingPromise = new Promise(() => {}) // Never resolves
    vi.mocked(authApi.login).mockReturnValue(pendingPromise)

    renderLoginPage()

    const usernameInput = screen.getByLabelText('Имя пользователя')
    const passwordInput = screen.getByLabelText('Пароль')
    const submitButton = screen.getByRole('button', { name: 'Войти' })

    fireEvent.change(usernameInput, { target: { value: 'admin' } })
    fireEvent.change(passwordInput, { target: { value: 'password' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Вход...')).toBeInTheDocument()
    })

    expect(usernameInput).toBeDisabled()
    expect(passwordInput).toBeDisabled()
    expect(submitButton).toBeDisabled()
  })
}) 