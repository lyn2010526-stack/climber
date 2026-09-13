import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MobileClusterPage } from '../MobileClusterPage';

vi.mock('../../ClusterPage', () => ({
  ClusterPage: () => <div>Cluster Content</div>,
}));

describe('MobileClusterPage', () => {
  it('renders ClusterPage content', async () => {
    render(<MobileClusterPage />);
    await waitFor(() => {
      expect(screen.getByText('Cluster Content')).toBeDefined();
    });
  });
});
