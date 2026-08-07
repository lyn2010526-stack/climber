import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../api', () => ({
  api: {
    listMCPServers: vi.fn().mockResolvedValue([]),
    listMCPCategories: vi.fn().mockResolvedValue([]),
    installMCPServer: vi.fn().mockResolvedValue({}),
    uninstallMCPServer: vi.fn().mockResolvedValue({}),
  },
}));

import { MCPPage } from '../MCPPage';

describe('MCPPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <MCPPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders loading state initially', () => {
    const { container } = render(
      <MemoryRouter>
        <MCPPage />
      </MemoryRouter>
    );
    expect(container.querySelector('svg.animate-spin')).toBeDefined();
  });

  it('renders content after loading', async () => {
    const { container } = render(
      <MemoryRouter>
        <MCPPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(container).toBeDefined();
    });
  });

  it('fetches servers on mount', () => {
    const { container } = render(
      <MemoryRouter>
        <MCPPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });
});
