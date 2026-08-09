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
          toastOptions={{
            className: 'apple-toast',
            style: {
              background: 'rgba(22, 22, 28, 0.92)',
              color: '#f2f2f7',
              backdropFilter: 'blur(24px) saturate(180%)',
              WebkitBackdropFilter: 'blur(24px) saturate(180%)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '14px',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
            },
          }}
        />
      </ErrorBoundary>
    </ThemeProvider>
  </StrictMode>,
)
