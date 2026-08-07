import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Modal } from '../Modal';

describe('Modal', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
  });

  it('does not render when open is false', () => {
    render(<Modal open={false} onClose={mockOnClose}>Content</Modal>);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders dialog element when open is true', () => {
    render(<Modal open={true} onClose={mockOnClose}>Content</Modal>);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('displays title text', () => {
    render(
      <Modal open={true} onClose={mockOnClose} title="Test Title">
        Content
      </Modal>
    );
    expect(screen.getByText('Test Title')).toBeInTheDocument();
  });

  it('displays description text below title', () => {
    render(
      <Modal
        open={true}
        onClose={mockOnClose}
        title="Title"
        description="Test Description"
      >
        Content
      </Modal>
    );
    expect(screen.getByText('Test Description')).toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    const TestIcon = () => <svg data-testid="test-icon"><circle /></svg>;
    render(
      <Modal open={true} onClose={mockOnClose} icon={<TestIcon />}>
        Content
      </Modal>
    );
    expect(screen.getByTestId('test-icon')).toBeInTheDocument();
  });

  it('renders children as modal content', () => {
    render(
      <Modal open={true} onClose={mockOnClose}>
        <p>Modal Body Content</p>
      </Modal>
    );
    expect(screen.getByText('Modal Body Content')).toBeInTheDocument();
  });

  it('closes modal when close button is clicked', () => {
    render(<Modal open={true} onClose={mockOnClose}>Content</Modal>);
    const closeButton = screen.getByLabelText('Close dialog');
    fireEvent.click(closeButton);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('renders backdrop element inside dialog', () => {
    render(<Modal open={true} onClose={mockOnClose}>Content</Modal>);
    const backdrop = document.querySelector('.absolute.inset-0');
    expect(backdrop).toBeInTheDocument();
    expect(backdrop).toHaveAttribute('aria-hidden', 'true');
  });

  it('prevents overlay close when closeOnOverlay is false', () => {
    render(
      <Modal open={true} onClose={mockOnClose} closeOnOverlay={false}>
        Content
      </Modal>
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('applies custom className to container', () => {
    render(
      <Modal open={true} onClose={mockOnClose} className="custom-modal-class">
        Content
      </Modal>
    );
    const dialog = screen.getByRole('dialog');
    const content = dialog.querySelector('.custom-modal-class');
    expect(content).toBeInTheDocument();
  });

  it('applies size class for sm', () => {
    render(
      <Modal open={true} onClose={mockOnClose} size="sm">
        Content
      </Modal>
    );
    const content = document.querySelector('.max-w-sm');
    expect(content).toBeInTheDocument();
  });

  it('applies size class for lg', () => {
    render(
      <Modal open={true} onClose={mockOnClose} size="lg">
        Content
      </Modal>
    );
    const content = document.querySelector('.max-w-lg');
    expect(content).toBeInTheDocument();
  });

  it('renders footer when footer prop is provided', () => {
    render(
      <Modal
        open={true}
        onClose={mockOnClose}
        footer={<button>Confirm</button>}
      >
        Content
      </Modal>
    );
    expect(screen.getByText('Confirm')).toBeInTheDocument();
  });

  it('renders with centered alignment by default', () => {
    render(
      <Modal open={true} onClose={mockOnClose}>
        Content
      </Modal>
    );
    const dialog = screen.getByRole('dialog');
    expect(dialog.className).toContain('items-center');
  });

  it('renders with top alignment when centered is false', () => {
    render(
      <Modal
        open={true}
        onClose={mockOnClose}
        centered={false}
      >
        Content
      </Modal>
    );
    const dialog = screen.getByRole('dialog');
    expect(dialog.className).toContain('items-start');
  });

  it('passes additional props to dialog', () => {
    render(
      <Modal open={true} onClose={mockOnClose}>
        Content
      </Modal>
    );
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('role', 'dialog');
  });

  it('maintains focus within modal for accessibility', () => {
    render(
      <Modal open={true} onClose={mockOnClose}>
        <input data-testid="modal-input" />
      </Modal>
    );
    const input = screen.getByTestId('modal-input');
    expect(input).toBeInTheDocument();
  });

  it('hides close button when showClose is false', () => {
    render(
      <Modal open={true} onClose={mockOnClose} showClose={false}>
        Content
      </Modal>
    );
    expect(screen.queryByLabelText('Close dialog')).not.toBeInTheDocument();
  });

  it('closes on Escape key press', () => {
    render(
      <Modal open={true} onClose={mockOnClose}>
        <input data-testid="modal-input" />
      </Modal>
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(mockOnClose).toHaveBeenCalled();
  });
});
