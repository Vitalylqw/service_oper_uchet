import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useAuthStore } from '@/stores/authStore'
import { authApi } from '@/api/client'
import type { LoginRequest } from '@/types/api'
import './LoginPage.css'

export default function LoginPage() {
  const [credentials, setCredentials] = useState<LoginRequest>({
    username: '',
    password: '',
  })
  const { login } = useAuthStore()

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: (data) => {
      login(data.access_token, data.user)
    },
    onError: (error: any) => {
      console.error('Login failed:', error)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (credentials.username && credentials.password) {
      loginMutation.mutate(credentials)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setCredentials((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Система Операционного Учета</h1>
        <p className="login-subtitle">Войдите в систему для продолжения</p>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="username">Имя пользователя</label>
            <input
              type="text"
              id="username"
              name="username"
              value={credentials.username}
              onChange={handleInputChange}
              required
              disabled={loginMutation.isPending}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Пароль</label>
            <input
              type="password"
              id="password"
              name="password"
              value={credentials.password}
              onChange={handleInputChange}
              required
              disabled={loginMutation.isPending}
            />
          </div>

          {loginMutation.error && (
            <div className="error">
              Ошибка входа: {(loginMutation.error as any)?.response?.data?.detail || 'Неверные учетные данные'}
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary login-button"
            disabled={loginMutation.isPending || !credentials.username || !credentials.password}
          >
            {loginMutation.isPending ? 'Вход...' : 'Войти'}
          </button>
        </form>

        <div className="login-demo">
          <p>Демо-пользователи:</p>
          <div className="demo-users">
            <div className="demo-user">
              <strong>admin</strong> / password (Администратор)
            </div>
            <div className="demo-user">
              <strong>analyst</strong> / password (Аналитик)
            </div>
            <div className="demo-user">
              <strong>viewer</strong> / password (Наблюдатель)
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 