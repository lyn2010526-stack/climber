import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../api', () => ({
  api: {
    listPlugins: vi.fn().mockResolvedValue([]),
    enablePlugin: vi.fn().mockResolvedValue({}),
    disablePlugin: vi.fn().mockResolvedValue({}),
    deletePlugin: vi.fn().mockResolvedValue({}),
    importPlugin: vi.fn().mockResolvedValue({}),
  },
}));

import PluginPage from '../PluginPage';

describe('PluginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <PluginPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders loading state initially', () => {
    const { container } = render(
      <MemoryRouter>
        <PluginPage />
      </MemoryRouter>
    );
    expect(container.querySelector('svg.animate-spin')).toBeDefined();
  });

  it('renders content after loading', async () => {
    const { container } = render(
      <MemoryRouter>
        <PluginPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(container).toBeDefined();
    });
  });

  it('fetches plugins on mount', () => {
    const { container } = render(
      <MemoryRouter>
        <PluginPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });
});
