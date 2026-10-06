import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginPage } from '../LoginPage';

vi.mock('../../i18n', () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { 'Content-Type': 'application/json' },
});

const loginResponse = {
  access_token: 'access-1',
  refresh_token: 'refresh-1',
  token_type: 'bearer',
  user: { user_id: 7, username: 'admin', scopes: ['admin'] },
};

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  localStorage.clear();
  window.location.hash = '';
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

async function fillAndSubmit(username: string, password: string) {
  const user = userEvent.setup();
  render(<LoginPage />);
  await user.type(screen.getByLabelText('auth.username'), username);
  await user.type(screen.getByLabelText('auth.password'), password);
  fireEvent.click(screen.getByRole('button', { name: 'auth.login_submit' }));
}

describe('LoginPage', () => {
  it('renders the branded login form with labelled fields', () => {
    render(<LoginPage />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByLabelText('auth.username')).toBeInTheDocument();
    expect(screen.getByLabelText('auth.password')).toHaveAttribute('type', 'password');
    expect(screen.getByRole('button', { name: 'auth.login_submit' })).toBeInTheDocument();
  });

  it('submits credentials, stores the session, and enters the app', async () => {
    fetchMock.mockResolvedValue(json(loginResponse));
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    render(<LoginPage onSuccess={onSuccess} />);
    await user.type(screen.getByLabelText('auth.username'), 'admin');
    await user.type(screen.getByLabelText('auth.password'), 'secret');
    fireEvent.click(screen.getByRole('button', { name: 'auth.login_submit' }));

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/login',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ username: 'admin', password: 'secret' }),
      }),
    );
    expect(localStorage.getItem('auth_token')).toBe('access-1');
    expect(localStorage.getItem('refresh_token')).toBe('refresh-1');
    expect(localStorage.getItem('user_info')).toBe(JSON.stringify(loginResponse.user));
    expect(window.location.hash).toBe('#chat');
  });

  it('shows the invalid-credentials copy for a 401 and does not enter the app', async () => {
    fetchMock.mockResolvedValue(json({ detail: 'Invalid credentials' }, 401));
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    render(<LoginPage onSuccess={onSuccess} />);
    await user.type(screen.getByLabelText('auth.username'), 'admin');
    await user.type(screen.getByLabelText('auth.password'), 'wrong');
    fireEvent.click(screen.getByRole('button', { name: 'auth.login_submit' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('auth.invalid_credentials');
    expect(onSuccess).not.toHaveBeenCalled();
    expect(localStorage.getItem('auth_token')).toBeNull();
    expect(window.location.hash).not.toBe('#chat');
  });

  it('shows the generic failure copy for a non-401 error', async () => {
    fetchMock.mockRejectedValue(new Error('network down'));
    await fillAndSubmit('admin', 'secret');
    expect(await screen.findByRole('alert')).toHaveTextContent('auth.login_failed');
  });

  it('requires both fields before submitting', async () => {
    render(<LoginPage />);
    fireEvent.click(screen.getByRole('button', { name: 'auth.login_submit' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('auth.required_fields');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('disables the form while the request is pending', async () => {
    let resolveRequest: (value: Response) => void;
    fetchMock.mockReturnValue(new Promise<Response>((resolve) => {
      resolveRequest = resolve;
    }));
    const user = userEvent.setup();
    render(<LoginPage />);
    await user.type(screen.getByLabelText('auth.username'), 'admin');
    await user.type(screen.getByLabelText('auth.password'), 'secret');
    fireEvent.click(screen.getByRole('button', { name: 'auth.login_submit' }));

    const submit = screen.getByRole('button', { name: 'auth.login_submit' });
    expect(submit).toBeDisabled();
    expect(screen.getByLabelText('auth.username')).toBeDisabled();

    resolveRequest!(json(loginResponse));
    await waitFor(() => expect(screen.getByRole('button', { name: 'auth.login_submit' })).toBeEnabled());
  });
});