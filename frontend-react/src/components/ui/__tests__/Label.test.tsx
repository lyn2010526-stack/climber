import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Label } from '../Label';

describe('Label', () => {
  it('renders with default props', () => {
    const { container } = render(<Label />);
    const label = container.querySelector('label');
    expect(label).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<Label className="custom-label-class" />);
    const label = container.querySelector('label');
    expect(label?.className).toContain('custom-label-class');
  });

  it('renders children content', () => {
    render(<Label>Label Text</Label>);
    expect(screen.getByText('Label Text')).toBeInTheDocument();
  });

  it('renders required asterisk when required prop is true', () => {
    const { container } = render(<Label required>Required Field</Label>);
    expect(screen.getByText('Required Field')).toBeInTheDocument();
    const asterisk = container.querySelector('span');
    expect(asterisk?.textContent).toBe('*');
  });

  it('renders without errors when no props provided', () => {
    const { container } = render(<Label />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('preserves additional HTML attributes', () => {
    const { container } = render(
      <Label data-testid="test-label" />
    );
    const label = container.querySelector('[data-testid="test-label"]');
    expect(label).toBeInTheDocument();
  });

  it('handles nested child elements', () => {
    render(
      <Label>
        <span>Nested Content</span>
      </Label>
    );
    expect(screen.getByText('Nested Content')).toBeInTheDocument();
  });

  it('allows dynamic text updates via rerender', () => {
    const { rerender } = render(<Label>Initial</Label>);
    rerender(<Label>Updated</Label>);
    expect(screen.getByText('Updated')).toBeInTheDocument();
  });

  it('works with form labels', () => {
    const { container } = render(
      <form>
        <Label htmlFor="input">Form Label</Label>
        <input id="input" type="text" />
      </form>
    );
    expect(screen.getByText('Form Label')).toBeInTheDocument();
  });

  it('applies block display and medium font weight', () => {
    const { container } = render(<Label>Test</Label>);
    const label = container.querySelector('label');
    expect(label?.className).toContain('block');
    expect(label?.className).toContain('font-medium');
  });
});
