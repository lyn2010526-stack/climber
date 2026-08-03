import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileFactoryPage } from '../MobileFactoryPage';

vi.mock('../../FactoryModePage', () => ({
  FactoryModePage: () => <div>Factory Content</div>,
}));

describe('MobileFactoryPage', () => {
  it('renders page header', () => {
    render(<MobileFactoryPage />);
    expect(screen.getByText('自主执行')).toBeDefined();
  });

  it('renders FactoryModePage content', () => {
    render(<MobileFactoryPage />);
    expect(screen.getByText('Factory Content')).toBeDefined();
  });
});
