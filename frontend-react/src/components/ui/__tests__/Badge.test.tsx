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
    expect(container.querySelector('.rounded-full')).not.toBeNull();
  });
});
