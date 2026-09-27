import { Component, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';
import i18n from '../i18n/config';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, info: { componentStack: string }) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error('ErrorBoundary caught:', error, info);
    this.props.onError?.(error, info);
  }

  override render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex flex-col items-center justify-center h-full p-8 text-center">
          <AlertTriangle size={40} className="mb-4 text-[var(--color-error)]" aria-hidden="true" />
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-2">{i18n.t('error_boundary.title')}</h2>
          <p className="text-sm text-[var(--color-text-secondary)] mb-4 max-w-md">
            {this.state.error?.message || i18n.t('error_boundary.description')}
          </p>
          <button type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
            className="rounded bg-[var(--color-accent)] px-4 py-2 text-sm text-[var(--color-accent-text)] transition-colors hover:bg-[var(--color-accent-hover)]"
          >
            {i18n.t('error_boundary.retry')}
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
