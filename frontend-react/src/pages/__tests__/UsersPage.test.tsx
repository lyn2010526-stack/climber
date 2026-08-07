import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { UsersPage } from '../UsersPage';

describe('UsersPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <UsersPage title="Users" />
      </MemoryRouter>
    );
    expect(screen.getByText('Users')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
