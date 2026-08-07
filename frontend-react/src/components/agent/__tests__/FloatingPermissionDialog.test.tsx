import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FloatingPermissionDialog, type PermissionRequest } from '../FloatingPermissionDialog';

const mockRequests: PermissionRequest[] = [
  {
    id: '1',
    action: 'file_read',
    description: 'Read file /test.txt',
    severity: 'low',
    timestamp: Date.now(),
  },
  {
    id: '2',
    action: 'command',
    description: 'Run command: ls -la',
    severity: 'medium',
    timestamp: Date.now(),
  },
];

describe('FloatingPermissionDialog', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <FloatingPermissionDialog
        requests={mockRequests}
        onApprove={() => {}}
        onDeny={() => {}}
        onApproveAll={() => {}}
      />
    );
    expect(container).toBeDefined();
  });

  it('returns null when requests is empty', () => {
    const { container } = render(
      <FloatingPermissionDialog
        requests={[]}
        onApprove={() => {}}
        onDeny={() => {}}
        onApproveAll={() => {}}
      />
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders permission request description', () => {
    render(
      <FloatingPermissionDialog
        requests={mockRequests}
        onApprove={() => {}}
        onDeny={() => {}}
        onApproveAll={() => {}}
      />
    );
    expect(screen.getByText('Run command: ls -la')).toBeDefined();
  });

  it('calls onApprove when approve button is clicked', () => {
    const onApprove = vi.fn();
    render(
      <FloatingPermissionDialog
        requests={[mockRequests[0]]}
        onApprove={onApprove}
        onDeny={() => {}}
        onApproveAll={() => {}}
      />
    );
    const approveButtons = screen.getAllByText('允许执行');
    if (approveButtons.length > 0) {
      fireEvent.click(approveButtons[0]);
      expect(onApprove).toHaveBeenCalled();
    }
  });
});
