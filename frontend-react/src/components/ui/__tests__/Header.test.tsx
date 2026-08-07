import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Header } from '../Header';

describe('Header', () => {
  it('renders with default props', () => {
    const { container } = render(<Header />);
    expect(container.querySelector('.component')).not.toBeNull();
  });

  it('renders children', () => {
    render(<Header><span>Header Content</span></Header>);
    expect(screen.getByText('Header Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Header />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Header variant="accent" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--accent');
  });

  it('applies size class', () => {
    const { container } = render(<Header size="lg" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--lg');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Header disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Header loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Header className="header-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('header-custom');
  });
});
