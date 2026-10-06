import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ConnectionEditor, isValidConnectionUrl } from './ConnectionEditor';

const VALID = {
  url: 'https://api.example.com/v1',
  apiKey: 'sk-test-placeholder',
  model: 'gpt-4o',
};

function fillForm(overrides: Partial<typeof VALID> = {}) {
  const value = { ...VALID, ...overrides };
  fireEvent.change(screen.getByTestId('connection-url'), { target: { value: value.url } });
  fireEvent.change(screen.getByTestId('connection-api-key'), { target: { value: value.apiKey } });
  fireEvent.change(screen.getByTestId('connection-model'), { target: { value: value.model } });
}

describe('ConnectionEditor', () => {
  beforeEach(() => vi.clearAllMocks());

  it('validates endpoint URLs', () => {
    expect(isValidConnectionUrl('https://api.example.com/v1')).toBe(true);
    expect(isValidConnectionUrl('http://localhost:8080/v1')).toBe(true);
    expect(isValidConnectionUrl('api.example.com')).toBe(false);
    expect(isValidConnectionUrl('')).toBe(false);
  });

  it('keeps submit disabled until URL, key and model are all valid', () => {
    render(<ConnectionEditor onSubmit={vi.fn()} onCancel={vi.fn()} />);
    const submit = screen.getByTestId('connection-submit');
    expect(submit).toBeDisabled();

    fillForm({ url: 'not-a-url' });
    expect(submit).toBeDisabled();

    fillForm({ url: VALID.url, apiKey: '' });
    expect(submit).toBeDisabled();

    fillForm({ url: VALID.url, apiKey: VALID.apiKey, model: '' });
    expect(submit).toBeDisabled();

    fillForm();
    expect(submit).toBeEnabled();
  });

  it('surfaces the regex error when a URL is invalid and blurred', () => {
    render(<ConnectionEditor onSubmit={vi.fn()} onCancel={vi.fn()} />);
    const url = screen.getByTestId('connection-url');
    fireEvent.change(url, { target: { value: 'ftp://nope' } });
    fireEvent.blur(url);
    expect(url).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a valid http(s) URL');
  });

  it('submits the draft through onSubmit only', () => {
    const onSubmit = vi.fn();
    render(<ConnectionEditor onSubmit={onSubmit} onCancel={vi.fn()} />);
    fillForm();
    fireEvent.click(screen.getByTestId('connection-submit'));
    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit).toHaveBeenCalledWith(VALID);
  });

  it('masks the API key by default and reveals it on demand', () => {
    render(<ConnectionEditor onSubmit={vi.fn()} onCancel={vi.fn()} />);
    const key = screen.getByTestId('connection-api-key');
    expect(key).toHaveAttribute('type', 'password');
    fireEvent.click(screen.getByTestId('connection-reveal'));
    expect(key).toHaveAttribute('type', 'text');
    expect(screen.getByTestId('connection-reveal')).toHaveAttribute('aria-pressed', 'true');
  });

  it('copies the key to the clipboard without logging it', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    render(<ConnectionEditor onSubmit={vi.fn()} onCancel={vi.fn()} />);
    fillForm();
    fireEvent.click(screen.getByTestId('connection-copy'));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(VALID.apiKey));
  });

  it('seeds from initial and cancels without submitting', () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    render(<ConnectionEditor initial={VALID} onSubmit={onSubmit} onCancel={onCancel} />);
    expect(screen.getByTestId('connection-url')).toHaveValue(VALID.url);
    expect(screen.getByTestId('connection-api-key')).toHaveValue(VALID.apiKey);
    expect(screen.getByTestId('connection-model')).toHaveValue(VALID.model);
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onCancel).toHaveBeenCalledOnce();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
