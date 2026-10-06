import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowLeft, Plus, Trash2, Users } from 'lucide-react';
import { api, type ClusterNodeOut, type GroupOut } from '../api';
import { getClusterMembers, type ClusterMember } from '../services/cluster-service';
import { useTranslation } from '../i18n';
import { GroupRoom } from '../components/group/GroupRoom';
import { CollaborationWorkspace } from '../components/collaboration/CollaborationWorkspace';
import {
  AddMemberForm,
  ParticipantList,
  SidebarSection,
} from '../components/collaboration/CollaborationSidebar';
import { TaskSubmitForm } from '../components/collaboration/TaskSubmitForm';
import { useGroupTask } from '../components/collaboration/useGroupTask';
import { groupStatusLabel } from '../components/collaboration/taskStatus';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { PageHeader } from '../components/ui/PageHeader';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';

const MEMBER_ROLES = [
  'worker',
  'reviewer',
  'moderator',
  'manager',
  'observer',
];

/**
 * Cluster node roster with create + delete. Node deletion is admin-gated on
 * the backend, so a 403 is reported verbatim rather than hidden.
 */
function ClusterNodesSection() {
  const { t } = useTranslation();
  const [nodes, setNodes] = useState<ClusterNodeOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [nodeName, setNodeName] = useState('');
  const [nodeEndpoint, setNodeEndpoint] = useState('');
  const [nodeRole, setNodeRole] = useState('worker');
  const [busy, setBusy] = useState(false);

  const loadNodes = useCallback(async () => {
    setLoading(true);
    setError('');
    try { setNodes(await api.listClusterNodes()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : t('collaboration.cluster.load_failed', { defaultValue: 'Failed to load cluster nodes' })); }
    finally { setLoading(false); }
  }, [t]);
  useEffect(() => { void loadNodes(); }, [loadNodes]);

  const createNode = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!nodeName.trim() || busy) return;
    setBusy(true);
    setError('');
    try {
      await api.createCluster({
        name: nodeName.trim(),
        endpoint: nodeEndpoint.trim() || undefined,
        role: nodeRole,
      });
      setShowCreate(false);
      setNodeName('');
      setNodeEndpoint('');
      setNodeRole('worker');
      await loadNodes();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t('collaboration.cluster.create_failed', { defaultValue: 'Failed to create cluster node' }));
    } finally { setBusy(false); }
  };

  const deleteNode = async (node: ClusterNodeOut) => {
    if (busy) return;
    const label = node.name || node.id;
    if (!window.confirm(t('collaboration.cluster.delete_confirm', { name: label, defaultValue: `Delete cluster node "${label}"?` }))) return;
    setBusy(true);
    setError('');
    try {
      await api.deleteClusterNode(node.id);
      await loadNodes();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t('collaboration.cluster.delete_failed', { defaultValue: 'Failed to delete cluster node' }));
    } finally { setBusy(false); }
  };

  return (
    <section aria-label={t('collaboration.cluster.heading', { defaultValue: 'Cluster nodes' })} className="mt-8">
      <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] pb-[var(--space-4)]">
        <h2 className="text-[length:var(--text-base)] font-semibold">{t('collaboration.cluster.heading', { defaultValue: 'Cluster nodes' })}</h2>
        <Button size="sm" variant="outline" icon={<Plus size={14} />} onClick={() => setShowCreate(current => !current)}>
          {t('collaboration.cluster.create', { defaultValue: 'New node' })}
        </Button>
      </div>
      {showCreate && (
        <form className="mt-4 max-w-xl space-y-3 rounded-lg border border-[var(--color-border-subtle)] p-4" onSubmit={event => void createNode(event)}>
          <Input aria-label={t('collaboration.cluster.name_label', { defaultValue: 'Node name' })} placeholder={t('collaboration.cluster.name_label', { defaultValue: 'Node name' })} value={nodeName} onChange={event => setNodeName(event.target.value)} />
          <Input aria-label={t('collaboration.cluster.endpoint_label', { defaultValue: 'Endpoint (optional)' })} placeholder={t('collaboration.cluster.endpoint_label', { defaultValue: 'Endpoint (optional)' })} value={nodeEndpoint} onChange={event => setNodeEndpoint(event.target.value)} />
          <select
            aria-label={t('collaboration.cluster.role_label', { defaultValue: 'Role' })}
            value={nodeRole}
            onChange={event => setNodeRole(event.target.value)}
            className="h-9 rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] px-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-primary)]"
          >
            {MEMBER_ROLES.map(value => <option key={value} value={value}>{value}</option>)}
          </select>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={() => setShowCreate(false)}>{t('common.cancel')}</Button>
            <Button type="submit" size="sm" disabled={busy || !nodeName.trim()}>{t('common.create')}</Button>
          </div>
        </form>
      )}
      {error && <p role="alert" className="mt-3 text-sm text-[var(--color-error)]">{error}</p>}
      {loading ? (
        <div role="status" className="py-4"><SkeletonList count={2} /></div>
      ) : nodes.length === 0 && !error ? (
        <p className="py-4 text-sm text-[var(--color-text-muted)]">{t('collaboration.cluster.empty', { defaultValue: 'No cluster nodes yet' })}</p>
      ) : (
        <Card padding="none" className="mt-4 overflow-hidden">
          <ul className="divide-y divide-[var(--color-border-subtle)]">
            {nodes.map(node => (
              <li key={node.id} className="flex flex-wrap items-center gap-4 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="break-words text-sm font-semibold">{node.name || node.id}</p>
                  <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                    {[node.role, node.status, node.endpoint].filter(Boolean).join(' · ') || t('collaboration.not_reported')}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy}
                  aria-label={t('collaboration.cluster.delete_named', { name: node.name || node.id, defaultValue: `Delete node ${node.name || node.id}` })}
                  onClick={() => void deleteNode(node)}
                >
                  <Trash2 size={14} />
                </Button>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </section>
  );
}

type Group = GroupOut;

interface MemberPanelProps {
  members: ClusterMember[];
  /** Failure of the membership read; the roster is then unknown, not empty. */
  loadError: string;
  /** Failure of an add/remove call; the last known roster stays valid. */
  actionError: string;
  showAdd: boolean;
  editing: boolean;
  agentId: string;
  role: string;
  roleLabel: (role: string) => string;
  agentIdPlaceholder: string;
  onAgentIdChange: (value: string) => void;
  onRoleChange: (value: string) => void;
  onToggleAdd: () => void;
  onCancelAdd: () => void;
  onSubmitAdd: () => void;
  onRemove: (memberId: string) => void;
  onRetry: () => void;
  onMemberRoleChange: (memberId: string, role: string) => void;
}

/**
 * Members and topics are collaboration context, so they render in the sidebar
 * beside the workspace rather than as workspace sections.
 */
function MemberPanel({
  members,
  loadError,
  actionError,
  showAdd,
  editing,
  agentId,
  role,
  roleLabel,
  agentIdPlaceholder,
  onAgentIdChange,
  onRoleChange,
  onToggleAdd,
  onCancelAdd,
  onSubmitAdd,
  onRemove,
  onRetry,
  onMemberRoleChange,
}: MemberPanelProps) {
  const { t } = useTranslation();
  return (
    <SidebarSection
      title={t('collaboration.sidebar.members')}
      meta={members.length > 0 ? members.length : undefined}
      actions={
        <Button
          variant="ghost"
          size="xs"
          aria-expanded={showAdd}
          aria-label={t('collaboration.sidebar.add_member')}
          onClick={onToggleAdd}
        >
          <Plus size={12} />
        </Button>
      }
    >
      {actionError && (
        <p role="alert" className="px-1 py-2 text-xs text-[var(--color-error)]">
          {actionError}
        </p>
      )}
      {loadError && (
        <div className="px-1 py-2">
          <p role="alert" className="text-xs text-[var(--color-error)]">
            {loadError}
          </p>
          <Button variant="ghost" size="xs" className="mt-1" aria-label={t('collaboration.members.reload')} onClick={onRetry}>
            {t('collaboration.members.retry')}
          </Button>
        </div>
      )}
      <ParticipantList
        members={members}
        onRemove={onRemove}
        removing={editing}
        roleLabel={roleLabel}
        error={loadError}
        roles={MEMBER_ROLES}
        onRoleChange={onMemberRoleChange}
        roleChangeDisabled={editing}
      />
      {showAdd && (
        <AddMemberForm
          submitting={editing}
          agentId={agentId}
          role={role}
          agentIdPlaceholder={agentIdPlaceholder}
          roleLabel={roleLabel}
          roles={MEMBER_ROLES}
          onAgentIdChange={onAgentIdChange}
          onRoleChange={onRoleChange}
          onCancel={onCancelAdd}
          onSubmit={onSubmitAdd}
        />
      )}
    </SidebarSection>
  );
}

export function ClusterPage() {
  const { t } = useTranslation();
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeGroup, setActiveGroup] = useState<Group | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [topic, setTopic] = useState('');
  const [template, setTemplate] = useState(false);
  const [saving, setSaving] = useState(false);
  const [members, setMembers] = useState<ClusterMember[]>([]);
  const [membersError, setMembersError] = useState('');
  const [actionError, setActionError] = useState('');
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [agentId, setAgentId] = useState('');
  const [role, setRole] = useState('worker');
  const [editing, setEditing] = useState(false);
  const membersRequest = useRef(0);

  const groupId = activeGroup?.id ?? '';
  const { task, taskId, active, submitting, cancelling, error: taskError, cancelTask, resetTask, retryTask, refreshTask, submitTask } =
    useGroupTask(groupId);

  const roleLabel = useCallback(
    (value: string) => t(`workflows.role_${value}`),
    [t],
  );
  const agentIdPlaceholder = t('workflows.member_agent_id');

  const loadGroups = useCallback(async () => {
    setLoading(true);
    setError('');
    try { setGroups(await api.listGroups()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : t('collaboration.errors.load_groups')); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void loadGroups(); }, [loadGroups]);
  useEffect(() => () => { membersRequest.current += 1; }, []);

  const loadMembers = useCallback(async (targetGroupId: string) => {
    const request = ++membersRequest.current;
    setLoadingMembers(true);
    setMembersError('');
    setMembers([]);
    try {
      const result = await getClusterMembers(targetGroupId);
      if (request === membersRequest.current) {
        setMembers(result);
        setActionError('');
      }
    } catch (reason) {
      if (request === membersRequest.current) setMembersError(reason instanceof Error ? reason.message : t('collaboration.errors.load_members'));
    } finally {
      if (request === membersRequest.current) setLoadingMembers(false);
    }
  }, []);

  const openGroup = (group: Group) => {
    setActiveGroup(group);
    setShowAdd(false);
    setAgentId('');
    setRole('worker');
    setMembersError('');
    setActionError('');
    void loadMembers(group.id);
  };

  const leaveGroup = () => {
    membersRequest.current += 1;
    setActiveGroup(null);
    void loadGroups();
  };

  const editMember = async (memberId?: string) => {
    if (!activeGroup || editing || (!memberId && !agentId.trim())) return;
    const request = membersRequest.current;
    setEditing(true);
    setActionError('');
    try {
      if (memberId) await api.removeGroupMember(activeGroup.id, memberId);
      else await api.addGroupMember(activeGroup.id, { agent_id: agentId.trim(), role });
      if (request !== membersRequest.current) return;
      setShowAdd(false);
      setAgentId('');
      await loadMembers(activeGroup.id);
    } catch (reason) {
      if (request === membersRequest.current) setActionError(reason instanceof Error ? reason.message : t('collaboration.errors.update_member'));
    } finally { setEditing(false); }
  };

  const changeMemberRole = async (memberId: string, nextRole: string) => {
    if (!activeGroup || editing) return;
    const request = membersRequest.current;
    setEditing(true);
    setActionError('');
    try {
      await api.updateGroupMember(activeGroup.id, memberId, { role: nextRole });
      if (request !== membersRequest.current) return;
      await loadMembers(activeGroup.id);
    } catch (reason) {
      if (request === membersRequest.current) setActionError(reason instanceof Error ? reason.message : t('collaboration.errors.update_member'));
    } finally { setEditing(false); }
  };

  const deleteGroup = async (group: Group) => {
    if (saving) return;
    if (!window.confirm(t('collaboration.groups.delete_confirm', { name: group.name, defaultValue: `Delete group "${group.name}"? This cannot be undone.` }))) return;
    setSaving(true);
    setError('');
    try {
      await api.deleteGroup(group.id);
      await loadGroups();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t('collaboration.errors.delete_group', { defaultValue: 'Failed to delete group' }));
    } finally { setSaving(false); }
  };

  const handleMemberUpdate = useCallback((memberId: string, status: string) => {
    setMembers(current => current.map(member => member.id === memberId ? { ...member, status } : member));
  }, []);

  const handleTaskUpdate = useCallback((updatedTaskId: string) => {
    void refreshTask(updatedTaskId);
  }, [refreshTask]);

  return (
    <div className="h-full overflow-y-auto text-[var(--color-text-primary)]">
      <div className="mx-auto max-w-6xl p-4 md:p-6 lg:p-8">
        {activeGroup ? <>
          <Button variant="ghost" size="sm" icon={<ArrowLeft size={14} />} aria-label={t('collaboration.back_to_group_list')} onClick={leaveGroup}>{t('collaboration.back_to_list')}</Button>
          <h1 className="mt-4 border-b border-[var(--color-border-subtle)] pb-[var(--space-4)] text-[length:var(--text-base)] font-semibold break-words">{activeGroup.name}</h1>

          <div className="mt-6 grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(240px,320px)]">
            <div className="min-w-0">
              <CollaborationWorkspace
                task={{
                  taskId,
                  status: task?.status,
                  progress: task?.progress,
                  totalSteps: task?.total_steps,
                  objective: task?.objective,
                  result: task?.result,
                  error: task?.error,
                  cancelling,
                  requestError: taskError,
                }}
                 onCancel={() => void cancelTask()}
                 onReset={resetTask}
                 onRetry={retryTask}
              />
              <section aria-label={t('collaboration.aria.group_discussion')} className="mt-8 flex h-[60vh] min-h-80 flex-col border-t border-[var(--color-border-subtle)] pt-6">
                 <GroupRoom
                   groupId={activeGroup.id}
                   onMemberUpdate={handleMemberUpdate}
                   onTaskUpdate={handleTaskUpdate}
                 />
              </section>
            </div>

            <aside aria-label={t('collaboration.aria.sidebar')} className="min-w-0 lg:border-l lg:border-[var(--color-border-subtle)] lg:pl-6">
              <SidebarSection title={t('collaboration.sidebar.submit_task')}>
                <TaskSubmitForm
                  onSubmit={(objective, maxSteps) => void submitTask(objective, maxSteps)}
                  disabled={active}
                  submitting={submitting}
                />
              </SidebarSection>

              {loadingMembers
                ? <p role="status" aria-label={t('collaboration.aria.loading_members')} className="py-3 text-xs">{t('collaboration.members.loading')}</p>
                : <MemberPanel
                    members={members}
                    loadError={membersError}
                    actionError={actionError}
                    showAdd={showAdd}
                    editing={editing}
                    agentId={agentId}
                    role={role}
                    roleLabel={roleLabel}
                    agentIdPlaceholder={agentIdPlaceholder}
                    onAgentIdChange={setAgentId}
                    onRoleChange={setRole}
                    onToggleAdd={() => setShowAdd(current => !current)}
                    onCancelAdd={() => setShowAdd(false)}
                    onSubmitAdd={() => void editMember()}
                    onRemove={memberId => void editMember(memberId)}
                    onRetry={() => void loadMembers(activeGroup.id)}
                    onMemberRoleChange={(memberId, nextRole) => void changeMemberRole(memberId, nextRole)}
                  />}

              <SidebarSection title={t('collaboration.sidebar.topic')}>
                <p className="px-1 py-2 text-xs break-words text-[var(--color-text-secondary)]">
                  {activeGroup.topic || activeGroup.description || t('collaboration.topic_unset')}
                </p>
              </SidebarSection>
            </aside>
          </div>
        </> : <>
          <PageHeader title={t('collaboration.groups.heading')} icon={<Users size={20} />} className="border-b border-[var(--color-border-subtle)] pb-[var(--space-4)] [&_h1]:text-[length:var(--text-base)] [&_h1]:md:text-[length:var(--text-base)]" actions={<Button size="sm" icon={<Plus size={14} />} onClick={() => setShowCreate(true)}>{t('collaboration.groups.create')}</Button>} />
          {showCreate && <form className="mb-6 max-w-xl space-y-3 rounded-lg border border-[var(--color-border-subtle)] p-4" onSubmit={async event => {
            event.preventDefault();
            if (!name.trim() || saving) return;
            setSaving(true); setError('');
            try {
              await api.createGroup({
                name: name.trim(),
                topic: topic.trim(),
                template: template ? 'default' : undefined,
              });
              setShowCreate(false); setName(''); setTopic(''); setTemplate(false);
              await loadGroups();
            } catch (reason) { setError(reason instanceof Error ? reason.message : t('collaboration.errors.create_group')); }
            finally { setSaving(false); }
          }}>
            <Input aria-label={t('collaboration.groups.name_label')} placeholder={t('collaboration.groups.name_label')} value={name} onChange={event => setName(event.target.value)} />
            <Input aria-label={t('collaboration.groups.topic_label')} placeholder={t('collaboration.groups.topic_placeholder')} value={topic} onChange={event => setTopic(event.target.value)} />
            <label className="flex items-center gap-2 text-[length:var(--text-sm)] text-[var(--color-text-secondary)]"><input type="checkbox" checked={template} onChange={event => setTemplate(event.target.checked)} />{t('collaboration.groups.template_hint')}</label>
            <div className="flex justify-end gap-2"><Button type="button" variant="ghost" size="sm" onClick={() => setShowCreate(false)}>{t('common.cancel')}</Button><Button type="submit" size="sm" disabled={saving || !name.trim()}>{t('common.create')}</Button></div>
          </form>}
          {error && <div role="alert" className="mb-4 text-sm text-[var(--color-error)]"><p>{error}</p><Button variant="ghost" size="sm" onClick={loadGroups}>{t('collaboration.groups.reload')}</Button></div>}
          {loading ? <div role="status" aria-label={t('collaboration.groups.loading')} className="py-4"><SkeletonList count={3} /></div> : groups.length === 0 && !error ? (
            <Card padding="none" className="overflow-hidden">
              <EmptyState
                className="w-full"
                icon={<Users size={20} />}
                title={t('collaboration.groups.empty')}
                action={<Button size="sm" icon={<Plus size={14} />} onClick={() => setShowCreate(true)}>{t('collaboration.groups.create')}</Button>}
              />
            </Card>
          ) : (
            <Card padding="none" className="overflow-hidden">
              <div className="divide-y divide-[var(--color-border-subtle)]">
                {groups.map(group => <div key={group.id} className="flex flex-wrap items-center gap-4 px-4 py-4">
                  <div className="min-w-0 flex-1"><h2 className="break-words text-sm font-semibold">{group.name}</h2>              <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                    {typeof group.member_count === 'number' && Number.isInteger(group.member_count) && group.member_count >= 0 ? t('collaboration.groups.member_count', { count: group.member_count }) : t('collaboration.groups.member_count_unreported')} ·{' '}
                    {groupStatusLabel(group.status, t)}
                  </p></div>
                  <Button size="sm" variant="outline" onClick={() => openGroup(group)}>{t('collaboration.groups.enter')}</Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={saving}
                    aria-label={t('collaboration.groups.delete_named', { name: group.name, defaultValue: `Delete group ${group.name}` })}
                    onClick={() => void deleteGroup(group)}
                  >
                    <Trash2 size={14} />
                  </Button>
                </div>)}
              </div>
            </Card>
          )}

          <ClusterNodesSection />
        </>}
      </div>
    </div>
  );
}
