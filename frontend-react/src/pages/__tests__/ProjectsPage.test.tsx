import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ProjectsPage } from '../ProjectsPage';

describe('ProjectsPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <ProjectsPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <ProjectsPage title="Projects" />
      </MemoryRouter>
    );
    expect(screen.getByText('Projects')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <ProjectsPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
