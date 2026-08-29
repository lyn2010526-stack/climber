import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Toaster } from 'sonner'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import { ThemeProvider } from './hooks/useTheme'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <ErrorBoundary>
        <App />
        <Toaster
          position="top-center"
          theme="system"
          toastOptions={{
            className: 'product-toast',
            style: {
              background: 'var(--color-bg-surface-1)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border-default)',
              borderRadius: '10px',
              boxShadow: 'var(--shadow-lg)',
            },
          }}
        />
      </ErrorBoundary>
    </ThemeProvider>
  </StrictMode>,
)
