import { useCallback, useRef } from 'react';
import type { ChatStreamEvent } from '../types/chatEvents';
import {
  isFileEditTool,
  isSubTaskTool,
  toPreviewLines,
  useAnchoredStore,
  type InfoCardId,
  type SubAgentNode,
} from '../store/anchored';

/**
 * AI 驱动 UI 精准触发规则的落地层。
 *
 * 输入是逐帧归一化后的真实 SSE 事件（`ChatStreamEvent`），不是渲染后的 messages，
 * 也不含任何本地造数据。每条规则只改动自己负责的面板 / 状态，未命中的面板保持
 * 现状，默认不主动全展开。
 *
 * 规则映射（对照 docs/plans/frontend-anchored-ui.md 第三节）：
 * ① 进入规划        → 展开任务看板（beginPlanning）
 * ② 开始调用工具    → 状态栏"执行工具" + 登记运行中工具（noteToolCall）
 * ③ 工具执行完成    → 更新运行态；失败则自动展开结果块（noteToolResult）
 * ④ 拆分子任务      → 展开子 Agent 任务树并新增节点（expandForSubTask）
 * ⑤ 编辑代码 / 文件 → 自动展开文件预览并高亮变更（openFilePreview）
 * ⑥ 任务结束 5 秒后 → 折叠看板 / 树 / 预览（noteTurnEnd）
 * ⑦ 工具需要审批    → 输入区上方弹出审批弹窗（pushPopup）
 * ⑧ 错误 / 异常     → 状态栏变红并携带原因（noteError）
 *
 * 斜杠命令（⑨）与配置档切换（⑩）分别属于输入框与全局设置，不经事件流，此处不处理。
 */

/** 归一化审批弹窗标题 / 描述，便于调用方注入 i18n，测试时回退为稳定 key。 */
export interface PanelAutoRevealI18n {
  approvalTitle: () => string;
  approvalFallback: string;
}

const DEFAULT_I18N: PanelAutoRevealI18n = {
  approvalTitle: () => 'anchored.popup.approval_title',
  approvalFallback: 'anchored.popup.approval_required',
};

export interface PanelAutoRevealOptions {
  /** i18n 注入；缺省时使用稳定 key，界面层可在渲染时再翻译。 */
  i18n?: Partial<PanelAutoRevealI18n>;
}

/** 工具调用 id → 元信息；工具结果帧只带 id，需回溯工具名与入参。 */
interface ToolMeta {
  name: string;
  arguments: Record<string, unknown>;
  approvalId?: string;
}

export interface PanelRevealContext {
  /** 已见过的工具调用元信息（跨帧保持）。 */
  tools: Map<string, ToolMeta>;
  /** 已推送过审批弹窗的工具调用 id，避免重复堆叠。 */
  approvalSeen: Set<string>;
}

export function createPanelRevealContext(): PanelRevealContext {
  return { tools: new Map(), approvalSeen: new Set() };
}

function readPath(args: Record<string, unknown>): string | undefined {
  const candidate = args.path ?? args.file_path ?? args.filePath ?? args.filename;
  return typeof candidate === 'string' && candidate.length > 0 ? candidate : undefined;
}

function subTaskStatus(error: string | undefined, running: boolean): SubAgentNode['status'] {
  if (error && error.trim()) return 'error';
  return running ? 'running' : 'success';
}

/**
 * 单帧事件 → 面板动作的纯函数。返回被本帧改动过的卡片 id（便于测试断言"只动该动的"）。
 * 不读取 / 不伪造业务数据，所有内容均来自事件负载本身。
 */
export function reduceChatEventForPanels(
  event: ChatStreamEvent,
  ctx: PanelRevealContext,
  i18n: PanelAutoRevealI18n = DEFAULT_I18N,
): InfoCardId[] {
  const store = useAnchoredStore.getState();
  const touched: InfoCardId[] = [];

  switch (event.type) {
    case 'turn_started': {
      // ① 新任务 / 排队任务开始执行 → 进入规划阶段，展开任务看板。
      store.beginPlanning(event.message);
      touched.push('taskBoard');
      break;
    }

    case 'tool_call': {
      const { id, name, arguments: args, requiresApproval, description, severity } = event.toolCall;
      const toolId = id || `${name}:${ctx.tools.size}`;
      ctx.tools.set(toolId, { name, arguments: args });

      // ② 开始调用工具 → 状态栏"执行工具"，登记运行中工具。
      store.noteToolCall(toolId, name);

      // ④ 拆分子任务 → 展开子 Agent 任务树并新增节点（运行态）。
      if (isSubTaskTool(name)) {
        store.expandForSubTask({ id: toolId, name, status: 'running' });
        touched.push('subAgentTree');
      }

      // ⑦ 需要审批 → 推入弹窗栈（同一工具调用只推一次）。
      if (requiresApproval && !ctx.approvalSeen.has(toolId)) {
        ctx.approvalSeen.add(toolId);
        const path = readPath(args);
        const command = typeof args.command === 'string' ? args.command : undefined;
        store.pushPopup({
          kind: 'approval',
          title: i18n.approvalTitle(),
          description: description || name || i18n.approvalFallback,
          severity: severity ?? 'medium',
          ...(command ? { command } : {}),
          ...(path ? { path } : {}),
          payload: { toolCallId: toolId },
        });
      }
      break;
    }

    case 'tool_result': {
      const meta = ctx.tools.get(event.toolCallId);
      const failed = Boolean(event.error && event.error.trim());
      // ③ 工具完成 → 结束运行态；失败则自动展开结果块。
      store.noteToolResult(event.toolCallId, event.error);

      if (meta && isSubTaskTool(meta.name)) {
        store.expandForSubTask({
          id: event.toolCallId,
          name: meta.name,
          status: subTaskStatus(event.error, false),
          ...(event.error ? { detail: event.error } : {}),
        });
        touched.push('subAgentTree');
      }

      // ⑤ 编辑代码 / 文件且成功 → 展开文件预览并高亮变更。
      if (!failed && meta && isFileEditTool(meta.name)) {
        const path = readPath(meta.arguments) ?? meta.name;
        const lines = toPreviewLines(event.result);
        if (lines.length > 0) {
          store.openFilePreview({
            name: path.split('/').at(-1) ?? path,
            path,
            lines,
          });
          touched.push('filePreview');
        }
      }
      break;
    }

    case 'turn_done':
    case 'done': {
      // ⑥ 任务结束 → 标记回合结束，5 秒后自动折叠看板 / 树 / 预览。
      store.noteTurnEnd();
      touched.push('taskBoard', 'subAgentTree', 'filePreview');
      break;
    }

    case 'error': {
      // ⑧ 错误 / 异常 → 状态栏变红并携带原因。
      store.noteError(event.message);
      break;
    }

    case 'loop_status': {
      // ⑪ 写入 Pi 外层循环快照，供长任务循环面板读取。
      store.setLoopStatus({
        outerRound: event.outerRound,
        currentInput: event.currentInput,
        completed: event.completed,
        followupQueue: event.followupQueue,
        steeringQueue: event.steeringQueue,
        noProgressCount: event.noProgressCount,
      });
      break;
    }

    default:
      // text / thinking / runtime_report / input_status / unknown 不改面板显隐。
      break;
  }

  return touched;
}

/**
 * 把真实 SSE 事件流接到 anchored store 的面板联动钩子。
 *
 * 返回一个稳定回调，可直接传给 `useChat(sessionId, { onEvent })`。回调在下游
 * 事件处理的同一帧同步执行，避免逐帧 setState 造成的重复渲染；文本 / 思考增量
 * 不触发任何面板动作。
 *
 * 会话切换时应调用返回的 `reset()` 清空跨帧上下文，防止上一个会话的工具元信息
 * 串到新会话（AnchoredChatColumn 已在 sessionId 变更时重置 anchored store）。
 */
export function usePanelAutoReveal(options: PanelAutoRevealOptions = {}): {
  handleChatEvent: (event: ChatStreamEvent) => void;
  reset: () => void;
} {
  const ctxRef = useRef<PanelRevealContext>(createPanelRevealContext());
  const i18nRef = useRef<PanelAutoRevealI18n>({ ...DEFAULT_I18N, ...options.i18n });
  i18nRef.current = { ...DEFAULT_I18N, ...options.i18n };

  const handleChatEvent = useCallback((event: ChatStreamEvent) => {
    reduceChatEventForPanels(event, ctxRef.current, i18nRef.current);
  }, []);

  const reset = useCallback(() => {
    resetPanelRevealContext(ctxRef.current);
  }, []);

  return { handleChatEvent, reset };
}

/** 测试与重置用：清空钩子的跨帧上下文。 */
export function resetPanelRevealContext(ctx: PanelRevealContext): void {
  ctx.tools.clear();
  ctx.approvalSeen.clear();
}
