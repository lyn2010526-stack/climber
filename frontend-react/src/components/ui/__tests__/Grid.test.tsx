import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Grid } from '../Grid';

describe('Grid', () => {
  it('renders with default props', () => {
    const { container } = render(<Grid />);
    expect(container.querySelector('.component')).not.toBeNull();
  });

  it('renders children', () => {
    render(<Grid><span>Grid Content</span></Grid>);
    expect(screen.getByText('Grid Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Grid />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Grid variant="warning" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--warning');
  });

  it('applies size class', () => {
    const { container } = render(<Grid size="sm" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--sm');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Grid disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Grid loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Grid className="grid-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('grid-custom');
  });
});
