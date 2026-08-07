import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import {
  Toast,
  ToastContainer,
  ErrorBoundary,
  NetworkStatusBanner,
  InlineError,
  MessageSkeleton,
  DegradedModeBanner,
} from '../ErrorHandling';

describe('Toast', () => {
  it('renders toast with title', () => {
    render(
      <Toast type="info" title="Test Title" onClose={() => {}} />
    );
    expect(screen.getByText('Test Title')).toBeDefined();
  });

  it('renders description when provided', () => {
    render(
      <Toast type="success" title="Title" description="Some description" onClose={() => {}} />
    );
    expect(screen.getByText('Some description')).toBeDefined();
  });

  it('renders action button when provided', () => {
    const onClick = vi.fn();
    render(
      <Toast type="error" title="Error" action={{ label: 'Retry', onClick }} onClose={() => {}} />
    );
    fireEvent.click(screen.getByText('Retry'));
    expect(onClick).toHaveBeenCalled();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(
      <Toast type="warning" title="Warn" onClose={onClose} />
    );
    fireEvent.click(screen.getByLabelText('关闭通知'));
    expect(onClose).toHaveBeenCalled();
  });

  it('renders different types', () => {
    const { rerender } = render(<Toast type="info" title="info" onClose={() => {}} />);
    expect(screen.getByText('info')).toBeDefined();
    rerender(<Toast type="error" title="error" onClose={() => {}} />);
    expect(screen.getByText('error')).toBeDefined();
    rerender(<Toast type="warning" title="warn" onClose={() => {}} />);
    expect(screen.getByText('warn')).toBeDefined();
    rerender(<Toast type="success" title="ok" onClose={() => {}} />);
    expect(screen.getByText('ok')).toBeDefined();
  });
});

describe('ToastContainer', () => {
  it('renders multiple toasts', () => {
    const toasts = [
      { id: '1', type: 'info' as const, title: 'First' },
      { id: '2', type: 'error' as const, title: 'Second' },
    ];
    render(<ToastContainer toasts={toasts} onRemove={() => {}} />);
    expect(screen.getByText('First')).toBeDefined();
    expect(screen.getByText('Second')).toBeDefined();
  });

  it('calls onRemove when toast is closed', () => {
    const onRemove = vi.fn();
    const toasts = [{ id: '1', type: 'info' as const, title: 'Test' }];
    render(<ToastContainer toasts={toasts} onRemove={onRemove} />);
    fireEvent.click(screen.getByLabelText('关闭通知'));
    expect(onRemove).toHaveBeenCalledWith('1');
  });

  it('renders empty when no toasts', () => {
    const { container } = render(<ToastContainer toasts={[]} onRemove={() => {}} />);
    expect(container.querySelector('.fixed')).toBeDefined();
  });
});

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Child Content</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('Child Content')).toBeDefined();
  });

  it('renders fallback when error occurs', () => {
    const Throwing = () => {
      throw new Error('Test error');
    };
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <ErrorBoundary fallback={<div>Fallback Content</div>}>
        <Throwing />
      </ErrorBoundary>
    );
    expect(screen.getByText('Fallback Content')).toBeDefined();
    consoleSpy.mockRestore();
  });

  it('renders default error UI when no fallback', () => {
    const Throwing = () => {
      throw new Error('Crash!');
    };
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Throwing />
      </ErrorBoundary>
    );
    expect(screen.getByText('出错了')).toBeDefined();
    expect(screen.getByText('Crash!')).toBeDefined();
    consoleSpy.mockRestore();
  });
});

describe('NetworkStatusBanner', () => {
  it('renders offline banner when offline', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    render(<NetworkStatusBanner />);
    expect(screen.getByText('网络连接已断开')).toBeDefined();
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
  });

  it('does not render when online and no banner shown', () => {
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
    const { container } = render(<NetworkStatusBanner />);
    expect(container.firstChild).toBeNull();
  });
});

describe('InlineError', () => {
  it('renders error message', () => {
    render(<InlineError error="Something went wrong" />);
    expect(screen.getByText('Something went wrong')).toBeDefined();
  });

  it('renders retry button when onRetry provided and under max retries', () => {
    const onRetry = vi.fn();
    render(<InlineError error="Error" onRetry={onRetry} retryCount={0} maxRetries={3} />);
    fireEvent.click(screen.getByText(/重试/));
    expect(onRetry).toHaveBeenCalled();
  });

  it('does not render retry button when max retries reached', () => {
    const onRetry = vi.fn();
    render(<InlineError error="Error" onRetry={onRetry} retryCount={3} maxRetries={3} />);
    expect(screen.queryByText(/重试/)).toBeNull();
  });

  it('renders dismiss button when onDismiss provided', () => {
    const onDismiss = vi.fn();
    render(<InlineError error="Error" onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onDismiss).toHaveBeenCalled();
  });
});

describe('MessageSkeleton', () => {
  it('renders skeleton elements', () => {
    const { container } = render(<MessageSkeleton />);
    expect(container.querySelector('.animate-pulse')).toBeDefined();
    expect(container.querySelectorAll('.skeleton-shimmer').length).toBe(3);
  });
});

describe('DegradedModeBanner', () => {
  it('renders nothing when no features', () => {
    const { container } = render(<DegradedModeBanner features={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders banner with feature list', () => {
    render(<DegradedModeBanner features={['Feature A', 'Feature B']} />);
    expect(screen.getByText('部分功能暂不可用')).toBeDefined();
  });

  it('expands to show feature details', () => {
    render(<DegradedModeBanner features={['Feature A']} />);
    fireEvent.click(screen.getByText('部分功能暂不可用'));
    expect(screen.getByText('• Feature A')).toBeDefined();
  });
});
