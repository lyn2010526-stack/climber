import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Details } from '../Details';

describe('Details', () => {
  it('renders with default title', () => {
    const { container } = render(<Details />);
    expect(container.querySelector('h3')?.textContent).toBe('Details');
  });

  it('renders with custom title', () => {
    const { container } = render(<Details title="My Details" />);
    expect(container.querySelector('h3')?.textContent).toBe('My Details');
  });

  it('renders children', () => {
    render(<Details><span>Details Content</span></Details>);
    expect(screen.getByText('Details Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Details />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Details variant="info" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--info');
  });

  it('applies size class', () => {
    const { container } = render(<Details size="sm" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--sm');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Details disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Details loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Details className="details-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('details-custom');
  });
});
