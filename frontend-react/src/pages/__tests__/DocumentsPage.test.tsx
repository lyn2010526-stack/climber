import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DocumentsPage } from '../DocumentsPage';

describe('DocumentsPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <DocumentsPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <DocumentsPage title="Documents" />
      </MemoryRouter>
    );
    expect(screen.getByText('Documents')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <DocumentsPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
