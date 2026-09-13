import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MobileFactoryPage } from '../MobileFactoryPage';

vi.mock('../../FactoryModePage', () => ({
  FactoryModePage: () => <div>Factory Content</div>,
}));

describe('MobileFactoryPage', () => {
  it('renders FactoryModePage content', async () => {
    render(<MobileFactoryPage />);
    await waitFor(() => {
      expect(screen.getByText('Factory Content')).toBeDefined();
    });
  });
});
