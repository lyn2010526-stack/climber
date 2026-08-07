import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { List } from '../List';

describe('List', () => {
  it('renders with default props', () => {
    const { container } = render(<List />);
    expect(container.querySelector('.component')).not.toBeNull();
  });

  it('renders children', () => {
    render(<List><span>List Content</span></List>);
    expect(screen.getByText('List Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<List />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<List variant="secondary" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--secondary');
  });

  it('applies size class', () => {
    const { container } = render(<List size="sm" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--sm');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<List disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<List loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<List className="list-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('list-custom');
  });
});
