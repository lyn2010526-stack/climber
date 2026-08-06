import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from '../Badge';

describe('Badge', () => {
  it('renders children', () => {
    render(<Badge>New</Badge>);
    expect(screen.getByText('New')).toBeDefined();
  });

  it('renders different variants', () => {
    const { container } = render(<Badge variant="success">Success</Badge>);
    const badge = container.querySelector('div');
    expect(badge?.className).toContain('text-[var(--color-success)]');
    expect(badge?.className).toContain('bg-[var(--color-success-subtle)]');
  });

  it('applies default variant class', () => {
    const { container } = render(<Badge>Default</Badge>);
    const badge = container.querySelector('div');
    expect(badge?.className).toContain('text-[var(--color-text-secondary)]');
  });

  it('applies custom className', () => {
    const { container } = render(<Badge className="custom-badge">Default</Badge>);
    const badge = container.querySelector('div');
    expect(badge?.className).toContain('custom-badge');
  });
});
