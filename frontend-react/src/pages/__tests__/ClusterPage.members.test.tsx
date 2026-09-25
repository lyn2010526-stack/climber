import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../api';
import { ClusterPage } from '../ClusterPage';

vi.mock('../../api', () => ({ api: {
  listGroups: vi.fn(), getGroup: vi.fn(), addGroupMember: vi.fn(), removeGroupMember: vi.fn(),
} }));
vi.mock('../../components/group/GroupRoom', () => ({ GroupRoom: () => null }));
vi.mock('../../components/collaboration/CollaborationConsole', () => ({ CollaborationConsole: () => null }));

const member = { id: 'member-a', agent_id: 'agent-a', role: 'planner' };
const groups = ['a', 'b'].map(id => ({
  id, name: `Group ${id}`, description: '', status: 'active', member_count: 1, created_at: '',
}));

async function openMembers(index = 0) {
  render(<ClusterPage />);
  fireEvent.click(screen.getByRole('button', { name: '群组列表' }));
  const buttons = await screen.findAllByRole('button', { name: '成员' });
  fireEvent.click(buttons[index]);
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.listGroups).mockResolvedValue(groups);
});
afterEach(cleanup);

describe('ClusterPage persisted members', () => {
  it('loads real group detail and shows loading until it resolves', async () => {
    let resolve!: (value: unknown) => void;
    vi.mocked(api.getGroup).mockReturnValue(new Promise(done => { resolve = done; }));
    await openMembers();
    expect(api.getGroup).toHaveBeenCalledWith('a');
    expect(screen.getByRole('status', { name: '正在加载成员' })).toBeInTheDocument();
    expect(screen.queryByText('暂无成员')).not.toBeInTheDocument();
    await act(async () => resolve({ members: [member] }));
    expect(screen.getByText('agent-a')).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('shows an empty state only for an actual empty response', async () => {
    vi.mocked(api.getGroup).mockResolvedValue({ members: [] });
    await openMembers();
    expect(await screen.findByText('暂无成员')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows errors and retries without claiming empty membership', async () => {
    vi.mocked(api.getGroup).mockRejectedValueOnce(new Error('读取失败')).mockResolvedValue({ members: [member] });
    await openMembers();
    expect(await screen.findByRole('alert')).toHaveTextContent('读取失败');
    expect(screen.queryByText('暂无成员')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重新加载成员' }));
    expect(await screen.findByText('agent-a')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it.each([{}, { members: null }, { members: [{}] }])('rejects malformed member responses %j', async response => {
    vi.mocked(api.getGroup).mockResolvedValue(response);
    await openMembers();
    expect(await screen.findByRole('alert')).toHaveTextContent('响应格式异常');
    expect(screen.queryByText('暂无成员')).not.toBeInTheDocument();
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
    fireEvent.click(screen.getAllByRole('button', { name: '成员' })[1]);
    expect(await screen.findByText('agent-b')).toBeInTheDocument();
    await act(async () => resolve({ members: [member] }));
    expect(screen.queryByText('agent-a')).not.toBeInTheDocument();
    expect(screen.getByText('agent-b')).toBeInTheDocument();
  });

  it('reloads real membership after removal', async () => {
    vi.mocked(api.getGroup).mockResolvedValueOnce({ members: [member] }).mockResolvedValueOnce({ members: [] });
    vi.mocked(api.removeGroupMember).mockResolvedValue({ ok: true });
    await openMembers();
    fireEvent.click(await screen.findByRole('button', { name: '移除' }));
    expect(await screen.findByText('暂无成员')).toBeInTheDocument();
    expect(api.removeGroupMember).toHaveBeenCalledWith('a', 'member-a');
    expect(api.getGroup).toHaveBeenCalledTimes(2);
  });

  it('reloads real membership after addition', async () => {
    vi.mocked(api.getGroup).mockResolvedValueOnce({ members: [] }).mockResolvedValueOnce({ members: [member] });
    vi.mocked(api.addGroupMember).mockResolvedValue(member);
    await openMembers();
    fireEvent.click(await screen.findByRole('button', { name: '添加成员' }));
    fireEvent.change(screen.getByPlaceholderText('Agent ID'), { target: { value: 'agent-a' } });
    fireEvent.click(screen.getByRole('button', { name: '添加' }));
    expect(await screen.findByText('agent-a')).toBeInTheDocument();
    expect(api.addGroupMember).toHaveBeenCalledWith('a', expect.objectContaining({ agent_id: 'agent-a' }));
    expect(api.getGroup).toHaveBeenCalledTimes(2);
  });

  it('keeps persisted members visible when removal fails', async () => {
    vi.mocked(api.getGroup).mockResolvedValue({ members: [member] });
    vi.mocked(api.removeGroupMember).mockRejectedValue(new Error('移除失败'));
    await openMembers();
    fireEvent.click(await screen.findByRole('button', { name: '移除' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('移除失败');
    expect(screen.getByText('agent-a')).toBeInTheDocument();
  });

  it('keeps the panel closed when an earlier request completes', async () => {
    let resolve!: (value: unknown) => void;
    vi.mocked(api.getGroup).mockReturnValue(new Promise(done => { resolve = done; }));
    await openMembers();
    fireEvent.click(screen.getByRole('button', { name: '关闭成员面板' }));
    await act(async () => resolve({ members: [member] }));
    await waitFor(() => expect(screen.queryByText('群组成员')).not.toBeInTheDocument());
  });
});
