import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TeamsPage } from '../TeamsPage';

describe('TeamsPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <TeamsPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <TeamsPage title="Teams" />
      </MemoryRouter>
    );
    expect(screen.getByText('Teams')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <TeamsPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
