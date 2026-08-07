import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CalendarPage } from '../CalendarPage';

describe('CalendarPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <CalendarPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <CalendarPage title="Calendar" />
      </MemoryRouter>
    );
    expect(screen.getByText('Calendar')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <CalendarPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
