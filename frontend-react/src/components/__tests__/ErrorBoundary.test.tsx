import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from '../ErrorBoundary';

const GoodComponent = () => <div data-testid="good">All good</div>;
const BadComponent = () => {
  throw new Error('Test error');
};

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <GoodComponent />
      </ErrorBoundary>
    );
    expect(screen.getByTestId('good')).toBeDefined();
  });

  it('renders fallback UI when child throws', () => {
    render(
      <ErrorBoundary>
        <BadComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeDefined();
    expect(screen.getByText('Test error')).toBeDefined();
  });

  it('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div data-testid="custom">Custom error</div>}>
        <BadComponent />
      </ErrorBoundary>
    );
    expect(screen.getByTestId('custom')).toBeDefined();
  });

  it('calls onError callback when error occurs', () => {
    const onError = vi.fn();
    render(
      <ErrorBoundary onError={onError}>
        <BadComponent />
      </ErrorBoundary>
    );
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({ componentStack: expect.any(String) })
    );
  });

  it('shows Try Again button in fallback', () => {
    render(
      <ErrorBoundary>
        <BadComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText('Try Again')).toBeDefined();
  });

  it('renders custom fallback content', () => {
    render(
      <ErrorBoundary fallback={<div data-testid="custom-fallback">Custom UI</div>}>
        <BadComponent />
      </ErrorBoundary>
    );
    expect(screen.getByTestId('custom-fallback')).toBeDefined();
  });
});
