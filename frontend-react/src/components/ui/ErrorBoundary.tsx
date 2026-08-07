import React, { Component } from 'react';
import type { ErrorInfo } from 'react';
import { cn } from '../../lib/utils';
import { AlertTriangle, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';

export interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  showDetails?: boolean;
  className?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null, showDetails: false };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    this.props.onError?.(error, errorInfo);
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false });
  };

  toggleDetails = () => {
    this.setState(prev => ({ showDetails: !prev.showDetails }));
  };

  override render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      const { error, errorInfo, showDetails } = this.state;
      const shouldShowDetails = this.props.showDetails !== false;

      return (
        <div className={cn('flex items-center justify-center min-h-[300px] p-[var(--space-8)]', this.props.className)}>
          <div className="text-center max-w-md">
            <div className="w-16 h-16 rounded-full bg-[var(--color-danger-subtle)] flex items-center justify-center mx-auto mb-[var(--space-4)]">
              <AlertTriangle className="w-[var(--icon-2xl)] h-[var(--icon-2xl)] text-[var(--color-danger)]" />
            </div>
            <h3 className="text-[var(--font-size-lg)] font-semibold text-[var(--text-primary)] mb-[var(--space-2)]">
              Something went wrong
            </h3>
            <p className="text-[var(--font-size-sm)] text-[var(--text-muted)] mb-[var(--space-6)] leading-[var(--line-height-relaxed)]">
              {error?.message || 'An unexpected error occurred. Please try again.'}
            </p>
            <div className="flex items-center justify-center gap-[var(--space-2)]">
              <button
                onClick={this.handleRetry}
                className={cn(
                  'inline-flex items-center gap-[var(--space-2)] h-[var(--size-md)] px-[var(--space-4)] text-[var(--font-size-sm)] font-medium rounded-[var(--radius-lg)]',
                  'bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] transition-colors'
                )}
              >
                <RefreshCw className="w-[var(--icon-sm)] h-[var(--icon-sm)]" />
                Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                className={cn(
                  'inline-flex items-center gap-[var(--space-2)] h-[var(--size-md)] px-[var(--space-4)] text-[var(--font-size-sm)] font-medium rounded-[var(--radius-lg)]',
                  'border border-[var(--border-default)] bg-[var(--surface-bg)] text-[var(--text-primary)] hover:bg-[var(--surface-bg-hover)] transition-colors'
                )}
              >
                Reload Page
              </button>
            </div>
            {shouldShowDetails && errorInfo && (
              <div className="mt-[var(--space-6)] text-left">
                <button
                  onClick={this.toggleDetails}
                  className="flex items-center gap-[var(--space-1)] text-[var(--font-size-xs)] text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors mx-auto"
                  aria-expanded={showDetails}
                >
                  {showDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  {showDetails ? 'Hide' : 'Show'} error details
                </button>
                {showDetails && (
                  <div className="mt-[var(--space-2)] p-[var(--space-3)] bg-[var(--surface-bg-subtle)] border border-[var(--border-subtle)] rounded-[var(--radius-lg)] text-left overflow-auto max-h-48">
                    <pre className="text-[10px] text-[var(--color-danger)] font-mono whitespace-pre-wrap break-all">
                      {error?.toString()}
                      {'\n\n'}
                      {errorInfo.componentStack}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export { ErrorBoundary };
