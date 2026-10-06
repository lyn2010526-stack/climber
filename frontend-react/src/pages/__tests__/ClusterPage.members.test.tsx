import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../api';
import { ClusterPage } from '../ClusterPage';
import i18n from '../../i18n';

vi.mock('../../api', () => ({ api: {
  listGroups: vi.fn(), getGroup: vi.fn(), addGroupMember: vi.fn(), removeGroupMember: vi.fn(),
} }));
vi.mock('../../components/group/GroupRoom', () => ({ GroupRoom: () => null }));

const member = { id: 'member-a', agent_id: 'agent-a', role: 'worker', status: 'active' };
const groups = ['a', 'b'].map(id => ({
  id, name: `Group ${id}`, description: '', status: 'active', member_count: 1, created_at: '',
}));

async function openMembers(index = 0) {
  render(<ClusterPage />);
  const buttons = await screen.findAllByRole('button', { name: 'Enter' });
  fireEvent.click(buttons[index]);
  await screen.findByRole('complementary', { name: 'Collaboration sidebar' });
}

beforeEach(async () => {
  await i18n.changeLanguage('en');
  vi.resetAllMocks();
  vi.mocked(api.listGroups).mockResolvedValue(groups);
});
afterEach(cleanup);

function sidebar() {
  return screen.getByRole('complementary', { name: 'Collaboration sidebar' });
}

describe('ClusterPage persisted members', () => {
  it.each([
    [0, '0 members'],
    [undefined, 'Member count not reported'],
    [-1, 'Member count not reported'],
  ])('distinguishes the reported member count %s from missing data', async (count, label) => {
    vi.mocked(api.listGroups).mockResolvedValue([{ ...groups[0], member_count: count }] as never);
    render(<ClusterPage />);
    expect(await screen.findByText(`${label} · Active`)).toBeInTheDocument();
  });

  it('loads real group detail and shows loading until it resolves', async () => {
    let resolve!: (value: unknown) => void;
    vi.mocked(api.getGroup).mockReturnValue(new Promise(done => { resolve = done; }));
    await openMembers();
    expect(api.getGroup).toHaveBeenCalledWith('a');
    expect(screen.getByRole('status', { name: 'Loading members' })).toBeInTheDocument();
    expect(within(sidebar()).queryByText('No members')).not.toBeInTheDocument();
    await act(async () => resolve({ members: [member] }));
    expect(screen.getByText('agent-a')).toBeInTheDocument();
    expect(screen.queryByRole('status', { name: 'Loading members' })).not.toBeInTheDocument();
  });

  it('shows an empty state only for an actual empty response', async () => {
    vi.mocked(api.getGroup).mockResolvedValue({ members: [] });
    await openMembers();
    expect(await screen.findByText('No members')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows errors and retries without claiming empty membership', async () => {
    vi.mocked(api.getGroup).mockRejectedValueOnce(new Error('读取失败')).mockResolvedValue({ members: [member] });
    await openMembers();
    expect(await screen.findByRole('alert')).toHaveTextContent('读取失败');
    expect(within(sidebar()).queryByText('No members')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Reload members' }));
    expect(await screen.findByText('agent-a')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it.each([{}, { members: null }, { members: [{}] }])('rejects malformed member responses %j', async response => {
    vi.mocked(api.getGroup).mockResolvedValue(response);
    await openMembers();
    expect(await screen.findByRole('alert')).toHaveTextContent(i18n.t('api_errors.cluster_members_invalid'));
    expect(within(sidebar()).queryByText('No members')).not.toBeInTheDocument();
  });

  it('accepts a persisted member with a nullable agent id', async () => {
    vi.mocked(api.getGroup).mockResolvedValue({ members: [{ ...member, agent_id: null }] });
    await openMembers();
    expect(await screen.findByText('member-a')).toBeInTheDocument();
  });

  it('ignores responses for a previously selected group', async () => {
    let resolve!: (value: unknown) => void;
    vi.mocked(api.getGroup).mockReturnValueOnce(new Promise(done => { resolve = done; }))
      .mockResolvedValueOnce({ members: [{ ...member, id: 'member-b', agent_id: 'agent-b' }] });
    await openMembers();
    fireEvent.click(screen.getByRole('button', { name: 'Back to group list' }));
    const groupButtons = await screen.findAllByRole('button', { name: 'Enter' });
    fireEvent.click(groupButtons[1]);
    await screen.findByRole('complementary', { name: 'Collaboration sidebar' });
    expect(await screen.findByText('agent-b')).toBeInTheDocument();
    await act(async () => resolve({ members: [member] }));
    expect(screen.queryByText('agent-a')).not.toBeInTheDocument();
    expect(screen.getByText('agent-b')).toBeInTheDocument();
  });

  it('reloads real membership after removal', async () => {
    vi.mocked(api.getGroup).mockResolvedValueOnce({ members: [member] }).mockResolvedValueOnce({ members: [] });
    vi.mocked(api.removeGroupMember).mockResolvedValue({ ok: true });
    await openMembers();
    fireEvent.click(await screen.findByRole('button', { name: 'Remove agent-a' }));
    expect(await screen.findByText('No members')).toBeInTheDocument();
    expect(api.removeGroupMember).toHaveBeenCalledWith('a', 'member-a');
    expect(api.getGroup).toHaveBeenCalledTimes(2);
  });

  it('reloads real membership after addition', async () => {
    vi.mocked(api.getGroup).mockResolvedValueOnce({ members: [] }).mockResolvedValueOnce({ members: [member] });
    vi.mocked(api.addGroupMember).mockResolvedValue(member);
    await openMembers();
    fireEvent.click(await screen.findByRole('button', { name: 'Add member' }));
    fireEvent.change(screen.getByPlaceholderText('Agent ID'), { target: { value: 'agent-a' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    expect(await screen.findByText('agent-a')).toBeInTheDocument();
    expect(api.addGroupMember).toHaveBeenCalledWith('a', expect.objectContaining({ agent_id: 'agent-a' }));
    expect(api.getGroup).toHaveBeenCalledTimes(2);
  });

  it('keeps persisted members visible when removal fails', async () => {
    vi.mocked(api.getGroup).mockResolvedValue({ members: [member] });
    vi.mocked(api.removeGroupMember).mockRejectedValue(new Error('移除失败'));
    await openMembers();
    fireEvent.click(await screen.findByRole('button', { name: 'Remove agent-a' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('移除失败');
    expect(screen.getByText('agent-a')).toBeInTheDocument();
  });

  it('keeps the panel closed when an earlier request completes', async () => {
    let resolve!: (value: unknown) => void;
    vi.mocked(api.getGroup).mockReturnValue(new Promise(done => { resolve = done; }));
    await openMembers();
    fireEvent.click(screen.getByRole('button', { name: 'Back to group list' }));
    await act(async () => resolve({ members: [member] }));
    await waitFor(() =>
      expect(screen.queryByRole('complementary', { name: 'Collaboration sidebar' })).not.toBeInTheDocument(),
    );
  });
});
