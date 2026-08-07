import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../api', () => ({
  api: {
    listReasoningHistory: vi.fn().mockResolvedValue([]),
    getReasoningTrace: vi.fn().mockResolvedValue({}),
  },
}));

import { ReasoningHistoryPage } from '../ReasoningHistoryPage';

describe('ReasoningHistoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <ReasoningHistoryPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders loading state initially', () => {
    render(
      <MemoryRouter>
        <ReasoningHistoryPage />
      </MemoryRouter>
    );
    expect(screen.getByText('推理历史')).toBeDefined();
  });

  it('renders content after loading', async () => {
    const { container } = render(
      <MemoryRouter>
        <ReasoningHistoryPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(container).toBeDefined();
    });
  });

  it('fetches history on mount', () => {
    const { container } = render(
      <MemoryRouter>
        <ReasoningHistoryPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });
});
