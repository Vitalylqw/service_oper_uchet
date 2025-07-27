/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_APP_TITLE: string
  readonly VITE_APP_VERSION: string
  // Добавьте другие переменные окружения по мере необходимости
}

interface ImportMeta {
  readonly env: ImportMetaEnv
} 