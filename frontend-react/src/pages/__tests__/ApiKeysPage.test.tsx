import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ApiKeysPage } from '../ApiKeysPage';

vi.mock('../../api', () => ({
  api: {
    listApiKeys: vi.fn().mockResolvedValue([]),
    addApiKey: vi.fn().mockResolvedValue({}),
    deleteApiKey: vi.fn().mockResolvedValue({}),
  },
}));

describe('ApiKeysPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>
    );
    expect(screen.getByText('API Keys')).toBeDefined();
  });

  it('renders add key button', () => {
    render(
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>
    );
    expect(screen.getAllByText('Add Key').length).toBeGreaterThan(0);
  });

  it('renders empty state message after loading', async () => {
    render(
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>
    );
    expect(await screen.findByText('No API keys')).toBeDefined();
  });
});
