import { Network, Plus, Hash, Users, Wrench } from 'lucide-react';
import type { ClusterState } from './useClusterState';

export function GroupsView({ state }: { state: ClusterState }) {
  const {
    groups,
    showCreateGroup, setShowCreateGroup,
    groupName, setGroupName,
    groupTopic, setGroupTopic,
    useTemplate, setUseTemplate,
    createGroup,
    setViewMode,
    managingGroupId, setManagingGroupId,
    members, loadingMembers,
    showAddMember, setShowAddMember,
    memberForm, setMemberForm,
    addMember, removeMember,
    openGroup, openManageMembers,
  } = state;

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
          <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">智能体群组</h1>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">多智能体协作空间</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode('cluster')}
                className="px-3 py-1.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            >
              集群视图
            </button>
            <button
              onClick={() => setShowCreateGroup(true)}
              className="flex items-center gap-1 px-3 py-1.5 text-xs bg-[var(--color-accent)] text-white rounded-xl hover:bg-[var(--color-accent-hover)] transition-all duration-200 active:scale-[0.97]"
            >
              <Plus size={12} />
              新建群组
            </button>
          </div>
        </div>

        {/* Create Group Form */}
        {showCreateGroup && (
          <div className="p-4 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl space-y-3">
            <input
              type="text"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              placeholder="群组名称..."
              className="w-full px-3 py-2 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
            />
            <input
              type="text"
              value={groupTopic}
              onChange={(e) => setGroupTopic(e.target.value)}
              placeholder="讨论主题（可选）..."
              className="w-full px-3 py-2 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
            />
            <label className="flex items-center gap-2 text-xs text-[var(--color-text-secondary)] cursor-pointer">
              <input
                type="checkbox"
                checked={useTemplate}
                onChange={(e) => setUseTemplate(e.target.checked)}
                className="rounded border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-accent)] focus:ring-[var(--color-accent)]/50"
              />
              快速开始：自动添加 Planner + Executor + Reviewer 默认成员
            </label>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => { setShowCreateGroup(false); setUseTemplate(false); }}
                className="px-3 py-1.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                 取消
              </button>
              <button
                onClick={createGroup}
                disabled={!groupName.trim()}
                className="px-3 py-1.5 text-xs bg-[var(--color-accent)] text-white rounded-xl hover:bg-[var(--color-accent-hover)] disabled:opacity-50 transition-all duration-200"
              >
                 创建
              </button>
            </div>
          </div>
        )}

        {/* Member Management Panel */}
        {managingGroupId && (
          <div className="p-4 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-[var(--color-text-primary)]">群组成员</h3>
              <button
                onClick={() => setManagingGroupId(null)}
                className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                关闭
              </button>
            </div>

            {loadingMembers ? (
              <div className="text-xs text-[var(--color-text-muted)]">加载中...</div>
            ) : (
              <>
                {/* Add Member Form */}
                {showAddMember ? (
                  <div className="p-3 bg-[var(--color-bg-surface-2)] rounded-xl space-y-2">
                    <input
                      type="text"
                      value={memberForm.agent_id}
                      onChange={(e) => setMemberForm({ ...memberForm, agent_id: e.target.value })}
                      placeholder="Agent ID"
                      className="w-full px-2 py-1.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)]"
                    />
                    <select
                      value={memberForm.role}
                      onChange={(e) => setMemberForm({ ...memberForm, role: e.target.value })}
                      className="w-full px-2 py-1.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)]"
                    >
                      <option value="planner">Planner</option>
                      <option value="researcher">Researcher</option>
                      <option value="executor">Executor</option>
                      <option value="auditor">Auditor</option>
                      <option value="participant">Participant</option>
                      <option value="observer">Observer</option>
                    </select>
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setShowAddMember(false)}
                        className="px-2 py-1 text-xs text-[var(--color-text-muted)]"
                      >
                        取消
                      </button>
                      <button
                        onClick={addMember}
                        disabled={!memberForm.agent_id.trim()}
                        className="px-2 py-1 text-xs bg-[var(--color-accent)] text-white rounded-xl disabled:opacity-50 transition-all duration-200"
                      >
                        添加
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowAddMember(true)}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition-colors"
                  >
                    <Plus size={12} />
                    添加成员
                  </button>
                )}

                {/* Members List */}
                <div className="space-y-2">
                  {members.map((member) => (
                    <div
                      key={member.id}
                      className="flex items-center justify-between p-2 bg-white/[0.02] border border-[var(--color-border-subtle)] rounded-xl"
                    >
                      <div>
                        <span className="text-xs text-[var(--color-text-primary)]">{member.agent_id || member.id}</span>
                        <span className="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-[var(--color-accent)]/10 text-[var(--color-accent)] border border-[var(--color-accent)]/20">
                          {member.role}
                        </span>
                      </div>
                      <button
                        onClick={() => removeMember(member.id)}
                        className="text-[10px] text-[var(--color-error)] hover:text-red-300 transition-colors"
                      >
                        移除
                      </button>
                    </div>
                  ))}
                  {members.length === 0 && (
                    <p className="text-xs text-[var(--color-text-muted)] text-center py-2">暂无成员</p>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {/* Groups List */}
        {groups.length === 0 ? (
          <div className="text-center py-12">
            <Network size={40} className="mx-auto text-[var(--color-text-muted)]/30" />
             <p className="text-sm text-[var(--color-text-muted)] mt-3">暂无群组</p>
             <p className="text-xs text-[var(--color-text-muted)]/60 mt-1">创建一个群组以开始多智能体协作</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {groups.map((group) => (
              <div
                key={group.id}
                className="p-4 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl hover:border-[var(--color-accent)]/30 transition-all duration-200"
              >
                <div className="flex items-center gap-2">
                  <Hash size={14} className="text-[var(--color-accent)]" />
                  <span className="text-sm font-medium text-[var(--color-text-primary)]">{group.name}</span>
                  <span className={`ml-auto px-2 py-0.5 text-[10px] rounded-full ${
                    group.status === 'active' ? 'bg-[var(--color-success)]/10 text-[var(--color-success)] border border-[var(--color-success)]/20' : 'bg-white/[0.03] text-[var(--color-text-muted)] border border-[var(--color-border-subtle)]'
                  }`}>
                    {group.status}
                  </span>
                </div>
                {group.description && (
                  <p className="text-[11px] text-[var(--color-text-muted)] mt-2 line-clamp-2">{group.description}</p>
                )}
                <div className="flex items-center gap-3 mt-3 text-[10px] text-[var(--color-text-muted)]">
                  <span>{group.member_count} 名成员</span>
                  <span>{new Date(group.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-[var(--color-border-subtle)]">
                  <button
                    onClick={() => openGroup(group.id, 'chat')}
                    className="flex items-center gap-1 px-2 py-1 text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] bg-white/[0.03] border border-[var(--color-border-subtle)] rounded-xl hover:bg-white/[0.06] transition-all duration-200"
                  >
                    <Users size={10} />
                    Chat
                  </button>
                  <button
                    onClick={() => openGroup(group.id, 'collab')}
                    className="flex items-center gap-1 px-2 py-1 text-[10px] text-[var(--color-accent)] bg-[var(--color-accent)]/10 hover:bg-[var(--color-accent)]/20 border border-[var(--color-accent)]/20 rounded-xl transition-all duration-200"
                  >
                    <Wrench size={10} />
                    自动协作
                  </button>
                  <button
                    onClick={() => openManageMembers(group.id)}
                    className="flex items-center gap-1 px-2 py-1 text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] bg-white/[0.03] border border-[var(--color-border-subtle)] rounded-xl hover:bg-white/[0.06] transition-all duration-200"
                  >
                    <Users size={10} />
                    管理
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
