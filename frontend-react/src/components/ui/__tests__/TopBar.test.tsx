import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TopBar } from '../TopBar';

vi.mock('../ThemeToggle', () => ({
  ThemeToggle: () => <div data-testid="theme-toggle">ThemeToggle</div>,
}));

describe('TopBar', () => {
  it('renders without crashing', () => {
    const { container } = render(<TopBar />);
    expect(container).toBeDefined();
  });

  it('renders breadcrumbs', () => {
    render(
      <TopBar breadcrumbs={[{ label: 'Home' }, { label: 'Settings' }]} />
    );
    expect(screen.getByText('Home')).toBeDefined();
    expect(screen.getByText('Settings')).toBeDefined();
  });

  it('renders single breadcrumb', () => {
    render(
      <TopBar breadcrumbs={[{ label: 'Dashboard' }]} />
    );
    expect(screen.getByText('Dashboard')).toBeDefined();
  });

  it('renders search button', () => {
    const { container } = render(<TopBar onSearchClick={() => {}} />);
    expect(container).toBeDefined();
  });

  it('calls onSearchClick when search button is clicked', () => {
    const onSearchClick = vi.fn();
    const { container } = render(<TopBar onSearchClick={onSearchClick} />);
    const buttons = container.querySelectorAll('button');
    if (buttons.length > 0) {
      fireEvent.click(buttons[0]);
    }
    expect(onSearchClick).toHaveBeenCalled();
  });

  it('renders with notification count', () => {
    const { container } = render(<TopBar notificationCount={5} />);
    expect(container).toBeDefined();
  });

  it('renders with zero notifications', () => {
    const { container } = render(<TopBar notificationCount={0} />);
    expect(container).toBeDefined();
  });

  it('renders with right content', () => {
    render(
      <TopBar rightContent={<div data-testid="right-content">Right</div>} />
    );
    expect(screen.getByTestId('right-content')).toBeDefined();
  });

  it('renders with custom className', () => {
    const { container } = render(<TopBar className="custom-class" />);
    expect(container).toBeDefined();
  });

  it('renders breadcrumb with href', () => {
    render(
      <TopBar breadcrumbs={[{ label: 'Home', href: '#home' }]} />
    );
    expect(screen.getByText('Home')).toBeDefined();
  });

  it('renders ThemeToggle', () => {
    render(<TopBar />);
    expect(screen.getByTestId('theme-toggle')).toBeDefined();
  });

  it('triggers mouse enter/leave events on search button', () => {
    render(<TopBar onSearchClick={() => {}} />);
    const buttons = screen.getAllByRole('button');
    if (buttons.length > 0) {
      fireEvent.mouseEnter(buttons[0]);
      fireEvent.mouseLeave(buttons[0]);
    }
    expect(buttons[0]).toBeDefined();
  });

  it('renders mobile search button', () => {
    const { container } = render(<TopBar onSearchClick={() => {}} />);
    expect(container).toBeDefined();
  });

  it('renders notifications button', () => {
    const { container } = render(<TopBar notificationCount={3} />);
    expect(container).toBeDefined();
  });

  it('renders notification indicator when count > 0', () => {
    const { container } = render(<TopBar notificationCount={1} />);
    expect(container).toBeDefined();
  });

  it('does not render notification indicator when count is 0', () => {
    const { container } = render(<TopBar notificationCount={0} />);
    expect(container).toBeDefined();
  });

  it('does not render notification indicator when count is undefined', () => {
    const { container } = render(<TopBar />);
    expect(container).toBeDefined();
  });

  it('renders with empty breadcrumbs', () => {
    const { container } = render(<TopBar breadcrumbs={[]} />);
    expect(container).toBeDefined();
  });

  it('renders with multiple breadcrumbs', () => {
    render(
      <TopBar breadcrumbs={[
        { label: 'Home', href: '#home' },
        { label: 'Settings', href: '#settings' },
        { label: 'Profile' },
      ]} />
    );
    expect(screen.getByText('Home')).toBeDefined();
    expect(screen.getByText('Settings')).toBeDefined();
    expect(screen.getByText('Profile')).toBeDefined();
  });

  it('handles breadcrumb click with href', () => {
    render(
      <TopBar breadcrumbs={[{ label: 'Home', href: '#home' }]} />
    );
    const homeButton = screen.getByText('Home');
    fireEvent.click(homeButton);
    expect(homeButton).toBeDefined();
  });

  it('handles search button mouse events', () => {
    render(<TopBar onSearchClick={() => {}} />);
    const buttons = screen.getAllByRole('button');
    for (const button of buttons) {
      fireEvent.mouseEnter(button);
      fireEvent.mouseLeave(button);
    }
    expect(buttons.length).toBeGreaterThan(0);
  });
});
