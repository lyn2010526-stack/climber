import { Component, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

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
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-2">Something went wrong</h2>
          <p className="text-sm text-[var(--color-text-secondary)] mb-4 max-w-md">
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-4 py-2 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-[var(--color-text-inverse)] text-sm rounded-[var(--radius-md)] transition-colors"
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
