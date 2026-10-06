import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { normalizeChatEvent, type ChatStreamEvent } from '../types/chatEvents';
import { resetAnchoredStore, useAnchoredStore } from '../store/anchored';
import {
  createPanelRevealContext,
  reduceChatEventForPanels,
  resetPanelRevealContext,
  usePanelAutoReveal,
} from './usePanelAutoReveal';

function call(id: string, name: string, args: Record<string, unknown> = {}): ChatStreamEvent {
  return { type: 'tool_call', toolCall: { id, name, arguments: args } };
}

beforeEach(() => resetAnchoredStore());
afterEach(() => vi.useRealTimers());

describe('reduceChatEventForPanels — AI 驱动 UI 触发规则', () => {
  it('① 进入规划展开任务看板，但不主动全展开其他卡片', () => {
    const ctx = createPanelRevealContext();
    const touched = reduceChatEventForPanels(
      { type: 'turn_started', inputId: 'i1', message: '重构计划' },
      ctx,
    );
    const state = useAnchoredStore.getState();
    expect(touched).toContain('taskBoard');
    expect(state.planning).toBe(true);
    expect(state.cardsOpen.taskBoard).toBe(true);
    expect(state.tasks.at(-1)?.name).toBe('重构计划');
    // 默认折叠的卡片保持折叠，不被规划事件误展开。
    expect(state.cardsOpen.subAgentTree).toBe(false);
    expect(state.cardsOpen.filePreview).toBe(false);
    expect(state.cardsOpen.ruleEditor).toBe(false);
  });

  it('② 开始调用工具 → 状态栏"执行工具"并登记运行中工具', () => {
    const ctx = createPanelRevealContext();
    reduceChatEventForPanels(call('t1', 'read_file', { path: '/a.ts' }), ctx);
    const state = useAnchoredStore.getState();
    expect(state.agentState).toBe('executing_tool');
    expect(state.runningToolIds).toEqual(['t1']);
  });

  it('③ 工具失败 → 移出运行态并记录待自动展开的结果块', () => {
    const ctx = createPanelRevealContext();
    reduceChatEventForPanels(call('t1', 'read_file'), ctx);
    reduceChatEventForPanels({ type: 'tool_result', toolCallId: 't1', result: '', error: 'boom' }, ctx);
    const state = useAnchoredStore.getState();
    expect(state.runningToolIds).toEqual([]);
    expect(state.failedToolIds).toContain('t1');
    expect(state.agentState).toBe('error');
    expect(state.agentStateMessage).toBe('boom');
  });

  it('④ 拆分子任务 → 展开子 Agent 任务树并按结果更新状态', () => {
    const ctx = createPanelRevealContext();
    reduceChatEventForPanels(call('sub1', 'spawn_agent', {}), ctx);
    expect(useAnchoredStore.getState().subAgentTree[0]).toMatchObject({ id: 'sub1', status: 'running' });
    expect(useAnchoredStore.getState().cardsOpen.subAgentTree).toBe(true);
    reduceChatEventForPanels({ type: 'tool_result', toolCallId: 'sub1', result: 'done', error: '' }, ctx);
    expect(useAnchoredStore.getState().subAgentTree[0].status).toBe('success');
  });

  it('⑤ 编辑文件成功 → 展开文件预览并保留真实变更标记', () => {
    const ctx = createPanelRevealContext();
    reduceChatEventForPanels(call('e1', 'apply_patch', { path: '/src/a.ts' }), ctx);
    reduceChatEventForPanels(
      { type: 'tool_result', toolCallId: 'e1', result: '+added\n-removed\n~changed', error: '' },
      ctx,
    );
    const state = useAnchoredStore.getState();
    expect(state.cardsOpen.filePreview).toBe(true);
    expect(state.previews[0]).toMatchObject({ name: 'a.ts', path: '/src/a.ts' });
    expect(state.previews[0].lines.map(line => line.marker)).toEqual(['add', 'del', 'change']);
  });

  it('⑤ 编辑文件失败时不展开文件预览', () => {
    const ctx = createPanelRevealContext();
    reduceChatEventForPanels(call('e1', 'apply_patch', { path: '/src/a.ts' }), ctx);
    reduceChatEventForPanels({ type: 'tool_result', toolCallId: 'e1', result: '', error: 'patch failed' }, ctx);
    expect(useAnchoredStore.getState().previews).toHaveLength(0);
  });

  it('⑥ 任务结束 5 秒后折叠看板、树、预览', () => {
    vi.useFakeTimers();
    const ctx = createPanelRevealContext();
    reduceChatEventForPanels({ type: 'turn_started', inputId: 'i1', message: 'task' }, ctx);
    reduceChatEventForPanels(call('sub1', 'spawn_agent'), ctx);
    reduceChatEventForPanels(call('e1', 'apply_patch', { path: '/a.ts' }), ctx);
    reduceChatEventForPanels({ type: 'tool_result', toolCallId: 'e1', result: '+x', error: '' }, ctx);
    expect(useAnchoredStore.getState().cardsOpen.taskBoard).toBe(true);

    reduceChatEventForPanels({ type: 'turn_done', status: 'completed' }, ctx);
    act(() => { vi.advanceTimersByTime(4999); });
    expect(useAnchoredStore.getState().cardsOpen.taskBoard).toBe(true);
    act(() => { vi.advanceTimersByTime(1); });
    const cards = useAnchoredStore.getState().cardsOpen;
    expect(cards.taskBoard).toBe(false);
    expect(cards.subAgentTree).toBe(false);
    expect(cards.filePreview).toBe(false);
  });

  it('⑦ 需要审批 → 推入弹窗栈且同一工具调用只推一次', () => {
    const ctx = createPanelRevealContext();
    const event: ChatStreamEvent = {
      type: 'tool_call',
      toolCall: { id: 'a1', name: 'run_command', arguments: { command: 'rm -rf x' }, requiresApproval: true, description: '危险命令', severity: 'high' },
    };
    reduceChatEventForPanels(event, ctx);
    reduceChatEventForPanels(event, ctx);
    const popups = useAnchoredStore.getState().popups;
    expect(popups).toHaveLength(1);
    expect(popups[0]).toMatchObject({ kind: 'approval', severity: 'high', command: 'rm -rf x', payload: { toolCallId: 'a1' } });
  });

  it('⑧ 错误 → 状态栏变红并携带原因', () => {
    const ctx = createPanelRevealContext();
    reduceChatEventForPanels({ type: 'error', message: 'model unavailable' }, ctx);
    expect(useAnchoredStore.getState().agentState).toBe('error');
    expect(useAnchoredStore.getState().agentStateMessage).toBe('model unavailable');
  });

  it('文本 / 思考事件不改动任何面板', () => {
    const ctx = createPanelRevealContext();
    const before = useAnchoredStore.getState().cardsOpen;
    expect(reduceChatEventForPanels({ type: 'text', delta: 'hi' }, ctx)).toEqual([]);
    expect(reduceChatEventForPanels({ type: 'thinking', delta: 'hmm' }, ctx)).toEqual([]);
    expect(useAnchoredStore.getState().cardsOpen).toEqual(before);
  });

  it('接受真实 SSE 归一化事件作为输入', () => {
    const ctx = createPanelRevealContext();
    const event = normalizeChatEvent({ event: 'tool_call', data: { id: 'tc-9', name: 'read_file' } });
    reduceChatEventForPanels(event, ctx);
    expect(useAnchoredStore.getState().runningToolIds).toEqual(['tc-9']);
  });

  it('⑪ LOOP_STATUS 帧写入外层循环快照，不改面板显隐', () => {
    const ctx = createPanelRevealContext();
    const before = useAnchoredStore.getState().cardsOpen;
    const touched = reduceChatEventForPanels(
      {
        type: 'loop_status',
        outerRound: 3,
        currentInput: 'fix login bug',
        completed: ['scan', 'parse'],
        followupQueue: ['retry deploy'],
        steeringQueue: [],
        noProgressCount: 2,
      },
      ctx,
    );
    expect(touched).toEqual([]);
    expect(useAnchoredStore.getState().loopStatus).toEqual({
      outerRound: 3,
      currentInput: 'fix login bug',
      completed: ['scan', 'parse'],
      followupQueue: ['retry deploy'],
      steeringQueue: [],
      noProgressCount: 2,
    });
    expect(useAnchoredStore.getState().cardsOpen).toEqual(before);
  });

  it('⑪ LOOP_STATUS 经 SSE 归一化写入快照', () => {
    const ctx = createPanelRevealContext();
    const event = normalizeChatEvent({
      event: 'loop_status',
      data: { outer_round: 5, current_input: 'x', completed: ['a'], followup_queue: [], steering_queue: [], no_progress_count: 0 },
    });
    reduceChatEventForPanels(event, ctx);
    expect(useAnchoredStore.getState().loopStatus).toMatchObject({ outerRound: 5, completed: ['a'] });
  });
});

describe('usePanelAutoReveal', () => {
  it('把真实事件流接入 store，并在 reset 后清空跨帧上下文', () => {
    const { result } = renderHook(() => usePanelAutoReveal());
    act(() => result.current.handleChatEvent(call('t1', 'read_file')));
    expect(useAnchoredStore.getState().runningToolIds).toEqual(['t1']);
    act(() => result.current.reset());
    act(() => result.current.handleChatEvent(call('e1', 'apply_patch', { path: '/b.ts' })));
    act(() => result.current.handleChatEvent({ type: 'tool_result', toolCallId: 'e1', result: '+x', error: '' }));
    expect(useAnchoredStore.getState().previews[0].path).toBe('/b.ts');
  });

  it('resetPanelRevealContext 清空工具与审批去重集合', () => {
    const ctx = createPanelRevealContext();
    reduceChatEventForPanels({ type: 'tool_call', toolCall: { id: 'a', name: 'run_command', arguments: {}, requiresApproval: true } }, ctx);
    expect(ctx.tools.size).toBe(1);
    expect(ctx.approvalSeen.size).toBe(1);
    resetPanelRevealContext(ctx);
    expect(ctx.tools.size).toBe(0);
    expect(ctx.approvalSeen.size).toBe(0);
  });
});
