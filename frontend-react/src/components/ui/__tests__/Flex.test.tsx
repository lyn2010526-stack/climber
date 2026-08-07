import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Flex } from '../Flex';

describe('Flex', () => {
  it('renders with default props', () => {
    const { container } = render(<Flex />);
    expect(container.querySelector('.component')).not.toBeNull();
  });

  it('renders children', () => {
    render(<Flex><span>Flex Content</span></Flex>);
    expect(screen.getByText('Flex Content')).toBeDefined();
  });

  it('applies default variant class', () => {
    const { container } = render(<Flex />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--default');
  });

  it('applies custom variant class', () => {
    const { container } = render(<Flex variant="secondary" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--secondary');
  });

  it('applies size class', () => {
    const { container } = render(<Flex size="lg" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--lg');
  });

  it('applies disabled class when disabled', () => {
    const { container } = render(<Flex disabled />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--disabled');
  });

  it('applies loading class when loading', () => {
    const { container } = render(<Flex loading />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('component--loading');
  });

  it('applies custom className', () => {
    const { container } = render(<Flex className="flex-custom" />);
    const wrapper = container.querySelector('.component');
    expect(wrapper?.className).toContain('flex-custom');
  });
});
