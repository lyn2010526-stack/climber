import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Main } from '../Main';

describe('Main', () => {
  it('renders with default props', () => {
    const { container } = render(<Main />);
    expect(container.querySelector('.component')).not.toBeNull();
  });

  it('renders children', () => {
    render(<Main><span>Main Content</span></Main>);
    expect(screen.getByText('Main Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Main />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Main variant="primary" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--primary');
  });

  it('applies size class', () => {
    const { container } = render(<Main size="xl" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--xl');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Main disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Main loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Main className="main-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('main-custom');
  });
});
