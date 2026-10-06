import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { SchedulerPage } from '../SchedulerPage';
import { api } from '../../api';
import i18n from '../../i18n';

vi.mock('../../api', () => ({ api: {
  listSchedulerTasks: vi.fn(), createSchedulerTask: vi.fn(),
  updateSchedulerTask: vi.fn(), deleteSchedulerTask: vi.fn(),
} }));

const task = { id: 'task-1', name: 'Daily check', description: 'Check workspace', cron: '0 9 * * *', enabled: true, last_run: null, next_run: null, run_count: 0 };

beforeEach(async () => {
  await i18n.changeLanguage('en');
  vi.resetAllMocks();
  vi.mocked(api.listSchedulerTasks).mockResolvedValue([task]);
  vi.mocked(api.updateSchedulerTask).mockResolvedValue({ ...task, enabled: false });
  vi.mocked(api.createSchedulerTask).mockResolvedValue(task);
  vi.mocked(api.deleteSchedulerTask).mockResolvedValue({});
});

describe('Scheduler task controls', () => {
  it('shows task data without inventing missing type or run timestamps', async () => {
    render(<SchedulerPage />);
    await screen.findByRole('article', { name: task.name });
    expect(screen.getByText('Enabled')).toBeVisible();
    expect(screen.getByText('Last: Not reported')).toBeVisible();
    expect(screen.getByText('Next: Not reported')).toBeVisible();
    expect(screen.getByText('Ran 0 times')).toBeVisible();
    expect(screen.queryByText('custom')).toBeNull();
  });

  it('sends explicit enabled state and displays the server acknowledgement', async () => {
    let resolve!: (value: unknown) => void;
    vi.mocked(api.updateSchedulerTask).mockReturnValue(new Promise(done => { resolve = done; }));
    render(<SchedulerPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Disable Daily check' }));
    expect(api.updateSchedulerTask).toHaveBeenCalledWith('task-1', { enabled: false });
    expect(screen.getByRole('button', { name: 'Disable Daily check' })).toBeDisabled();
    await act(async () => resolve({ ...task, enabled: false }));
    expect(screen.getByText('Stopped')).toBeVisible();
    expect(api.listSchedulerTasks).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Enable Daily check' }));
    expect(api.updateSchedulerTask).toHaveBeenLastCalledWith('task-1', { enabled: true });
    await act(async () => resolve(task));
  });

  it('keeps task controls available after a failed update', async () => {
    vi.mocked(api.updateSchedulerTask).mockRejectedValueOnce(new Error('failed'));
    render(<SchedulerPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Disable Daily check' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to update the task, please retry');
    expect(screen.getByText('Enabled')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Disable Daily check' }));
    await screen.findByText('Stopped');
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('preserves creation payload and retains the form on failure', async () => {
    vi.mocked(api.createSchedulerTask).mockRejectedValueOnce(new Error('failed'));
    render(<SchedulerPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Add task' }));
    fireEvent.change(screen.getByLabelText(i18n.t('scheduler.field.name_label')), { target: { value: '   ' } });
    expect(screen.getByRole('button', { name: 'Create' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText(i18n.t('scheduler.field.name_label')), { target: { value: 'Backup' } });
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Save files' } });
    fireEvent.change(screen.getByLabelText('Task type'), { target: { value: 'backup' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create' }));
    await screen.findByRole('alert');
    expect(screen.getByLabelText(i18n.t('scheduler.field.name_label'))).toHaveValue('Backup');
    expect(api.createSchedulerTask).toHaveBeenCalledWith({ name: 'Backup', description: 'Save files', cron: '*/5 * * * *', task_type: 'backup' });
    fireEvent.click(screen.getByRole('button', { name: 'Create' }));
    await waitFor(() => expect(screen.queryByLabelText(i18n.t('scheduler.field.name_label'))).toBeNull());
  });

  it('retains tasks on delete failure and removes them after acknowledgement', async () => {
    vi.mocked(api.deleteSchedulerTask).mockRejectedValueOnce(new Error('failed'));
    render(<SchedulerPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Delete Daily check' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to delete the task, please retry');
    expect(screen.getByRole('article', { name: task.name })).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Delete Daily check' }));
    await screen.findByText('No scheduled tasks');
    expect(api.deleteSchedulerTask).toHaveBeenCalledWith('task-1');
  });

  it('retries list loading errors', async () => {
    vi.mocked(api.listSchedulerTasks).mockRejectedValueOnce(new Error('offline'));
    render(<SchedulerPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Retry' }));
    await screen.findByRole('article', { name: task.name });
  });
});
