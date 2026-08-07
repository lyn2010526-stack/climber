import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { RegisterPage } from '../RegisterPage';

describe('RegisterPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <RegisterPage title="Register" />
      </MemoryRouter>
    );
    expect(screen.getByText('Register')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
