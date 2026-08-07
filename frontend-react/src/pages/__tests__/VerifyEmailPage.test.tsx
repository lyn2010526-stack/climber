import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { VerifyEmailPage } from '../VerifyEmailPage';

describe('VerifyEmailPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <VerifyEmailPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <VerifyEmailPage title="Verify Email" />
      </MemoryRouter>
    );
    expect(screen.getByText('Verify Email')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <VerifyEmailPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
