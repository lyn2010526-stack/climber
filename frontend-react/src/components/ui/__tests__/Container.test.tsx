import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Container } from '../Container';

describe('Container', () => {
  it('renders with default title', () => {
    const { container } = render(<Container />);
    expect(container.querySelector('h3')?.textContent).toBe('Container');
  });

  it('renders with custom title', () => {
    const { container } = render(<Container title="My Container" />);
    expect(container.querySelector('h3')?.textContent).toBe('My Container');
  });

  it('renders children', () => {
    render(<Container><span>Container Content</span></Container>);
    expect(screen.getByText('Container Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Container />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Container variant="secondary" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--secondary');
  });

  it('applies size class', () => {
    const { container } = render(<Container size="xl" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--xl');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Container disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Container loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Container className="container-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('container-custom');
  });
});
