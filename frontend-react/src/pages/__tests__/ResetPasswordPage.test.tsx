import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ResetPasswordPage } from '../ResetPasswordPage';

describe('ResetPasswordPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <ResetPasswordPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <ResetPasswordPage title="Reset Password" />
      </MemoryRouter>
    );
    expect(screen.getByText('Reset Password')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <ResetPasswordPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
