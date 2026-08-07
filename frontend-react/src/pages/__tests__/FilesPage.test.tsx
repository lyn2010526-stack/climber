import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { FilesPage } from '../FilesPage';

describe('FilesPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <FilesPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <FilesPage title="Files" />
      </MemoryRouter>
    );
    expect(screen.getByText('Files')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <FilesPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
