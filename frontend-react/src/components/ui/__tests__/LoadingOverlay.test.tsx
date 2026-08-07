import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LoadingOverlay, InlineSpinner } from '../LoadingOverlay';

describe('LoadingOverlay', () => {
  it('renders with default message', () => {
    render(<LoadingOverlay />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders with custom message', () => {
    render(<LoadingOverlay message="Custom Loading Message" />);
    expect(screen.getByText('Custom Loading Message')).toBeInTheDocument();
  });

  it('renders spinner element by default', () => {
    const { container } = render(<LoadingOverlay />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders custom spinner when spinner prop is provided', () => {
    const Custom = () => <div data-testid="custom-indicator">Custom</div>;
    render(<LoadingOverlay spinner={<Custom />} />);
    expect(screen.getByTestId('custom-indicator')).toBeInTheDocument();
  });

  it('hides default spinner when custom spinner provided', () => {
    const { container } = render(<LoadingOverlay spinner={<span>alt</span>} />);
    expect(container.querySelector('.animate-spin')).not.toBeInTheDocument();
  });

  it('handles empty message gracefully', () => {
    const { container } = render(<LoadingOverlay message="" />);
    expect(container.querySelector('[role="status"]')).toBeInTheDocument();
  });

  it('applies custom overlay class', () => {
    const { container } = render(<LoadingOverlay className="custom-overlay-class" />);
    const overlay = container.querySelector('[role="status"]');
    expect(overlay?.classList).toContain('custom-overlay-class');
  });

  it('applies blur by default', () => {
    const { container } = render(<LoadingOverlay />);
    const overlay = container.querySelector('[role="status"]');
    expect(overlay?.classList).toContain('backdrop-blur-sm');
  });

  it('omits blur when blur is false', () => {
    const { container } = render(<LoadingOverlay blur={false} />);
    const overlay = container.querySelector('[role="status"]');
    expect(overlay?.classList).not.toContain('backdrop-blur-sm');
  });

  it('supports transparent variant', () => {
    const { container } = render(<LoadingOverlay transparent />);
    const overlay = container.querySelector('[role="status"]');
    expect(overlay?.classList).toContain('bg-[var(--surface-bg)]/50');
  });

  it('supports non-transparent variant by default', () => {
    const { container } = render(<LoadingOverlay />);
    const overlay = container.querySelector('[role="status"]');
    expect(overlay?.classList).toContain('bg-[var(--surface-bg)]/80');
  });

  it('sets aria-label to the message for accessibility', () => {
    render(<LoadingOverlay message="Loading content" />);
    const status = screen.getByLabelText('Loading content');
    expect(status).toBeInTheDocument();
  });

  it('renders without errors when minimal props provided', () => {
    const { container } = render(<LoadingOverlay />);
    expect(container.firstChild).toBeInTheDocument();
  });
});

describe('InlineSpinner', () => {
  it('renders a loading spinner with role status', () => {
    render(<InlineSpinner />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders message when provided', () => {
    render(<InlineSpinner message="Saving..." />);
    expect(screen.getByText('Saving...')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<InlineSpinner className="custom-spinner-class" />);
    expect(container.firstChild?.className).toContain('custom-spinner-class');
  });

  it('sets aria-label to message', () => {
    render(<InlineSpinner message="Working" />);
    expect(screen.getByLabelText('Working')).toBeInTheDocument();
  });
});
