import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { OnboardingPage } from '../OnboardingPage';

describe('OnboardingPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <OnboardingPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <OnboardingPage title="Onboarding" />
      </MemoryRouter>
    );
    expect(screen.getByText('Onboarding')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <OnboardingPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
