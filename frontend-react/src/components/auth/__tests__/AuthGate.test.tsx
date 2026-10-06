import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthGate } from '../AuthGate';

vi.mock('../../../i18n', () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { 'Content-Type': 'application/json' },
});

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  localStorage.clear();
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function renderGate(ready: boolean) {
  return render(
    <AuthGate ready={ready}>
      <div data-testid="app-content">App content</div>
    </AuthGate>,
  );
}

describe('AuthGate', () => {
  it('makes no request before the boot surface is ready', () => {
    renderGate(false);
    expect(screen.getByTestId('app-content')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('probes the health endpoint once ready', async () => {
    fetchMock.mockImplementation(async () => json({ authentication_enabled: false }));
    renderGate(true);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/health'));
    expect(screen.getByTestId('app-content')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('caches the probe result so later boots skip the request', async () => {
    fetchMock.mockImplementation(async () => json({ authentication_enabled: false }));
    const { rerender } = renderGate(true);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/health'));
    fetchMock.mockClear();
    rerender(
      <AuthGate ready>
        <div data-testid="app-content">App content</div>
      </AuthGate>,
    );
    expect(fetchMock).not.toHaveBeenCalled();
    expect(localStorage.getItem('climber.auth.enabled')).toBe('0');
  });

  it('blocks the app with the login page when auth is enabled and no session exists', async () => {
    fetchMock.mockImplementation(async () => json({ authentication_enabled: true }));
    renderGate(true);
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'auth.login_submit' })).toBeInTheDocument();
    expect(localStorage.getItem('climber.auth.enabled')).toBe('1');
  });

  it('lets a stored session through and validates it against /auth/me', async () => {
    localStorage.setItem('auth_token', 'token-1');
    localStorage.setItem('climber.auth.enabled', '1');
    fetchMock.mockImplementation(async () => json({ username: 'admin' }));
    renderGate(true);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/me', expect.anything()));
    expect(screen.getByTestId('app-content')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('drops an invalid stored session back onto the login page', async () => {
    localStorage.setItem('auth_token', 'expired-token');
    localStorage.setItem('climber.auth.enabled', '1');
    fetchMock.mockImplementation(async (url) => {
      if (String(url) === '/api/v1/auth/me') return json({ detail: 'Authentication required' }, 401);
      return json({}, 404);
    });
    renderGate(true);
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(localStorage.getItem('auth_token')).toBeNull();
  });

  it('opens the login gate from a cached enabled flag without any request', async () => {
    localStorage.setItem('climber.auth.enabled', '1');
    renderGate(true);
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('fails open when the health probe is unavailable', async () => {
    fetchMock.mockImplementation(async () => {
      throw new Error('network down');
    });
    renderGate(true);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(screen.getByTestId('app-content')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('hides the login gate when a blocked session signs in', async () => {
    localStorage.setItem('climber.auth.enabled', '1');
    renderGate(true);
    const user = userEvent.setup();

    fetchMock.mockImplementation(async (url) => {
      if (String(url) === '/api/v1/auth/login') return json({ access_token: 'a', refresh_token: 'r' });
      return json({}, 404);
    });
    await user.type(screen.getByLabelText('auth.username'), 'admin');
    await user.type(screen.getByLabelText('auth.password'), 'secret');
    fireEvent.click(screen.getByRole('button', { name: 'auth.login_submit' }));

    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(screen.getByTestId('app-content')).toBeInTheDocument();
  });
});