import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import './DashboardLayout.css'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const navigationItems = [
    {
      path: '/dashboard',
      label: 'Главная',
      icon: '📊',
    },
    {
      path: '/deals',
      label: 'Сделки',
      icon: '📄',
    },
    {
      path: '/sessions',
      label: 'Синхронизация',
      icon: '🔄',
    },
  ]

  const handleLogout = () => {
    logout()
  }

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen)
  }

  const getRoleDisplayName = (role: string) => {
    switch (role) {
      case 'admin':
        return 'Администратор'
      case 'analyst':
        return 'Аналитик'
      case 'viewer':
        return 'Наблюдатель'
      default:
        return role
    }
  }

  return (
    <div className="dashboard-layout">
      <div className={`sidebar ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        <div className="sidebar-header">
          <h2>СОУ</h2>
          <button className="sidebar-toggle" onClick={toggleSidebar}>
            {isSidebarOpen ? '←' : '→'}
          </button>
        </div>

        {isSidebarOpen && (
          <nav className="sidebar-nav">
            {navigationItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-item ${location.pathname === item.path ? 'nav-item-active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </Link>
            ))}
          </nav>
        )}
      </div>

      <div className="main-content">
        <header className="header">
          <div className="header-left">
            <h1>Система Операционного Учета</h1>
          </div>
          <div className="header-right">
            <div className="user-info">
              <span className="user-name">{user?.username}</span>
              <span className="user-role">{getRoleDisplayName(user?.role || '')}</span>
            </div>
            <button className="btn btn-secondary logout-btn" onClick={handleLogout}>
              Выйти
            </button>
          </div>
        </header>

        <main className="content">
          {children}
        </main>
      </div>
    </div>
  )
} 