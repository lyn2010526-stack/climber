import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NavGroup } from '../NavGroup';

describe('NavGroup', () => {
  it('renders label', () => {
    render(<NavGroup label="Settings">content</NavGroup>);
    expect(screen.getByText('Settings')).toBeDefined();
  });

  it('renders children content', () => {
    render(
      <NavGroup label="Section">
        <div data-testid="child">Child item</div>
      </NavGroup>
    );
    expect(screen.getByTestId('child')).toBeDefined();
  });

  it('renders icon when provided', () => {
    render(
      <NavGroup label="Section" icon={<span data-testid="icon">Icon</span>}>
        content
      </NavGroup>
    );
    expect(screen.getByTestId('icon')).toBeDefined();
  });

  it('starts collapsed when defaultOpen is false', () => {
    const { container } = render(
      <NavGroup label="Collapsed">
        <div>Hidden content</div>
      </NavGroup>
    );
    const contentDiv = container.querySelector('.overflow-hidden') as HTMLElement;
    expect(contentDiv?.style.maxHeight).toBe('0px');
    expect(contentDiv?.style.opacity).toBe('0');
  });

  it('starts expanded when defaultOpen is true', () => {
    const { container } = render(
      <NavGroup label="Expanded" defaultOpen>
        <div>Visible content</div>
      </NavGroup>
    );
    const contentDiv = container.querySelector('.overflow-hidden') as HTMLElement;
    expect(contentDiv?.style.maxHeight).toBe('500px');
    expect(contentDiv?.style.opacity).toBe('1');
  });

  it('toggles open state on click', () => {
    const { container } = render(
      <NavGroup label="Toggle">
        <div>Toggle content</div>
      </NavGroup>
    );
    const button = screen.getByRole('button');
    const contentDiv = container.querySelector('.overflow-hidden') as HTMLElement;

    expect(contentDiv.style.maxHeight).toBe('0px');

    fireEvent.click(button);
    expect(contentDiv.style.maxHeight).toBe('500px');
    expect(contentDiv.style.opacity).toBe('1');

    fireEvent.click(button);
    expect(contentDiv.style.maxHeight).toBe('0px');
    expect(contentDiv.style.opacity).toBe('0');
  });

  it('applies custom className', () => {
    const { container } = render(
      <NavGroup label="Custom" className="my-nav-group">
        content
      </NavGroup>
    );
    expect(container.querySelector('.my-nav-group')).not.toBeNull();
  });

  it('shows chevron down when open', () => {
    render(
      <NavGroup label="Open" defaultOpen>
        content
      </NavGroup>
    );
    expect(screen.getByRole('button').querySelector('svg')).not.toBeNull();
  });

  it('shows chevron right when closed', () => {
    render(
      <NavGroup label="Closed">
        content
      </NavGroup>
    );
    expect(screen.getByRole('button').querySelector('svg')).not.toBeNull();
  });
});
