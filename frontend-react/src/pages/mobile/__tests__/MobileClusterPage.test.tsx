import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileClusterPage } from '../MobileClusterPage';

vi.mock('../../ClusterPage', () => ({
  ClusterPage: () => <div>Cluster Content</div>,
}));

describe('MobileClusterPage', () => {
  it('renders page header', () => {
    render(<MobileClusterPage />);
    expect(screen.getByText('集群协作')).toBeDefined();
  });

  it('renders ClusterPage content', () => {
    render(<MobileClusterPage />);
    expect(screen.getByText('Cluster Content')).toBeDefined();
  });
});
