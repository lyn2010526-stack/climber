import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ClimberMark } from '../ClimberMark';

describe('ClimberMark', () => {
  it('renders an inline svg marked aria-hidden', () => {
    const { container } = render(<ClimberMark />);
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    expect(svg).toHaveAttribute('aria-hidden', 'true');
  });

  it('applies default 16px size and custom size', () => {
    const { container: def } = render(<ClimberMark />);
    const defSvg = def.querySelector('svg')!;
    expect(defSvg).toHaveAttribute('width', '16');
    expect(defSvg).toHaveAttribute('height', '16');

    const { container } = render(<ClimberMark size={24} />);
    const svg = container.querySelector('svg')!;
    expect(svg).toHaveAttribute('width', '24');
    expect(svg).toHaveAttribute('height', '24');
    expect(svg).toHaveAttribute('viewBox', '0 0 24 24');
    expect(svg).toHaveAttribute('stroke-width', '2');
  });

  it('forwards className and uses currentColor by default', () => {
    const { container } = render(<ClimberMark className="workspace-mark-icon" />);
    const svg = container.querySelector('svg')!;
    expect(svg).toHaveClass('workspace-mark-icon');
    expect(svg).toHaveAttribute('stroke', 'currentColor');
  });

  it('honors an explicit color', () => {
    const { container } = render(<ClimberMark color="#863BFF" />);
    const svg = container.querySelector('svg')!;
    expect(svg).toHaveAttribute('stroke', '#863BFF');
  });

  it('contains the zigzag ascent and the summit node', () => {
    const { container } = render(<ClimberMark />);
    expect(container.querySelector('polyline')).toBeTruthy();
    expect(container.querySelector('rect')).toBeTruthy();
  });
});
