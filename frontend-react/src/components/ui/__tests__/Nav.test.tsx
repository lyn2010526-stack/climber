import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Nav } from '../Nav';

describe('Nav', () => {
  it('renders with default props', () => {
    const { container } = render(<Nav />);
    expect(container.querySelector('.component')).not.toBeNull();
  });

  it('renders children', () => {
    render(<Nav><span>Nav Content</span></Nav>);
    expect(screen.getByText('Nav Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Nav />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Nav variant="primary" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--primary');
  });

  it('applies size class', () => {
    const { container } = render(<Nav size="md" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--md');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Nav disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Nav loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Nav className="nav-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('nav-custom');
  });
});
