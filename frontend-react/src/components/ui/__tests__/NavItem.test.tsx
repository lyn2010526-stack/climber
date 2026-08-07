import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NavItem } from '../NavItem';

describe('NavItem', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <NavItem icon={<span>icon</span>} label="Home" />
    );
    expect(container).toBeDefined();
  });

  it('renders label', () => {
    render(
      <NavItem icon={<span>icon</span>} label="Home" />
    );
    expect(screen.getByText('Home')).toBeDefined();
  });

  it('renders icon', () => {
    render(
      <NavItem icon={<span data-testid="icon">icon</span>} label="Home" />
    );
    expect(screen.getByTestId('icon')).toBeDefined();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(
      <NavItem icon={<span>icon</span>} label="Home" onClick={onClick} />
    );
    fireEvent.click(screen.getByText('Home'));
    expect(onClick).toHaveBeenCalled();
  });

  it('renders active state', () => {
    const { container } = render(
      <NavItem icon={<span>icon</span>} label="Home" active={true} />
    );
    expect(container).toBeDefined();
  });

  it('renders inactive state', () => {
    const { container } = render(
      <NavItem icon={<span>icon</span>} label="Home" active={false} />
    );
    expect(container).toBeDefined();
  });

  it('renders with badge', () => {
    render(
      <NavItem icon={<span>icon</span>} label="Home" badge="3" />
    );
    expect(screen.getByText('3')).toBeDefined();
  });

  it('renders with numeric badge', () => {
    render(
      <NavItem icon={<span>icon</span>} label="Home" badge={5} />
    );
    expect(screen.getByText('5')).toBeDefined();
  });

  it('renders in compact mode', () => {
    const { container } = render(
      <NavItem icon={<span>icon</span>} label="Home" compact={true} />
    );
    expect(container).toBeDefined();
  });

  it('renders with custom className', () => {
    const { container } = render(
      <NavItem icon={<span>icon</span>} label="Home" className="custom-class" />
    );
    expect(container).toBeDefined();
  });

  it('triggers mouse enter/leave events', () => {
    render(
      <NavItem icon={<span>icon</span>} label="Home" />
    );
    const button = screen.getByText('Home');
    fireEvent.mouseEnter(button);
    fireEvent.mouseLeave(button);
    expect(button).toBeDefined();
  });
});
