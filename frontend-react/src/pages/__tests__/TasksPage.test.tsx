import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TasksPage } from '../TasksPage';

describe('TasksPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <TasksPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <TasksPage title="Tasks" />
      </MemoryRouter>
    );
    expect(screen.getByText('Tasks')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <TasksPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
