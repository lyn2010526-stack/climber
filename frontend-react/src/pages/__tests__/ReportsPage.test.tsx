import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ReportsPage } from '../ReportsPage';

describe('ReportsPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <ReportsPage title="Reports" />
      </MemoryRouter>
    );
    expect(screen.getByText('Reports')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
