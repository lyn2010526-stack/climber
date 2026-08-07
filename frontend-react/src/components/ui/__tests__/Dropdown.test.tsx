import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Dropdown } from '../Dropdown';

describe('Dropdown', () => {
  it('renders trigger element', () => {
    render(
      <Dropdown trigger={<button>Click me</button>}>
        Dropdown Content
      </Dropdown>
    );
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('renders with default props', () => {
    const { container } = render(
      <Dropdown trigger={<button>Trigger</button>}>
        Content
      </Dropdown>
    );
    const wrapper = container.querySelector('.relative.inline-block');
    expect(wrapper).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <Dropdown trigger={<button>Trigger</button>} className="custom-dropdown-class">
        Content
      </Dropdown>
    );
    const wrapper = container.querySelector('.custom-dropdown-class');
    expect(wrapper).toBeInTheDocument();
  });

  it('opens dropdown when trigger is clicked', () => {
    render(
      <Dropdown trigger={<button>Click me</button>}>
        Dropdown Content
      </Dropdown>
    );
    fireEvent.click(screen.getByText('Click me'));
    expect(screen.getByRole('menu')).toBeInTheDocument();
    expect(screen.getByText('Dropdown Content')).toBeInTheDocument();
  });

  it('closes dropdown when clicked again', () => {
    render(
      <Dropdown trigger={<button>Click me</button>}>
        Dropdown Content
      </Dropdown>
    );
    const trigger = screen.getByText('Click me');
    fireEvent.click(trigger);
    expect(screen.getByRole('menu')).toBeInTheDocument();
    fireEvent.click(trigger);
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  it('renders children content when open', () => {
    render(
      <Dropdown trigger={<button>Trigger</button>}>
        <span>Child 1</span>
        <span>Child 2</span>
      </Dropdown>
    );
    fireEvent.click(screen.getByText('Trigger'));
    expect(screen.getByText('Child 1')).toBeInTheDocument();
    expect(screen.getByText('Child 2')).toBeInTheDocument();
  });

  it('renders without errors when minimal props provided', () => {
    const { container } = render(
      <Dropdown trigger={<button>Trigger</button>}>
        Content
      </Dropdown>
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it('works with nested interactive elements', () => {
    const nestedClick = vi.fn();
    render(
      <Dropdown trigger={<button>Trigger</button>}>
        <button onClick={nestedClick}>Nested Button</button>
      </Dropdown>
    );
    fireEvent.click(screen.getByText('Trigger'));
    const button = screen.getByText('Nested Button');
    fireEvent.click(button);
    expect(nestedClick).toHaveBeenCalled();
  });

  it('supports controlled open state', () => {
    render(
      <Dropdown trigger={<button>Trigger</button>} open={true}>
        Controlled Content
      </Dropdown>
    );
    expect(screen.getByRole('menu')).toBeInTheDocument();
    expect(screen.getByText('Controlled Content')).toBeInTheDocument();
  });

  it('supports onOpenChange callback', () => {
    const onOpenChange = vi.fn();
    render(
      <Dropdown trigger={<button>Trigger</button>} onOpenChange={onOpenChange}>
        Content
      </Dropdown>
    );
    fireEvent.click(screen.getByText('Trigger'));
    expect(onOpenChange).toHaveBeenCalledWith(true);
  });

  it('renders with right alignment', () => {
    render(
      <Dropdown trigger={<button>Trigger</button>} align="right">
        Content
      </Dropdown>
    );
    fireEvent.click(screen.getByText('Trigger'));
    const menu = screen.getByRole('menu');
    expect(menu.className).toContain('right-0');
  });

  it('renders with center alignment', () => {
    render(
      <Dropdown trigger={<button>Trigger</button>} align="center">
        Content
      </Dropdown>
    );
    fireEvent.click(screen.getByText('Trigger'));
    const menu = screen.getByRole('menu');
    expect(menu.className).toContain('left-1/2');
  });

  it('renders with top side placement', () => {
    render(
      <Dropdown trigger={<button>Trigger</button>} side="top">
        Content
      </Dropdown>
    );
    fireEvent.click(screen.getByText('Trigger'));
    const menu = screen.getByRole('menu');
    expect(menu.className).toContain('bottom-full');
  });

  it('closes on Escape key press', () => {
    render(
      <Dropdown trigger={<button>Trigger</button>}>
        Content
      </Dropdown>
    );
    fireEvent.click(screen.getByText('Trigger'));
    expect(screen.getByRole('menu')).toBeInTheDocument();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });
});
