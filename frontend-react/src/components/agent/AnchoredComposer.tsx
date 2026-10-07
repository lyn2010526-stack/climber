import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowUp, CircleAlert, Paperclip, Square } from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { Button } from '../ui/Button';
import { ImageAttachmentBar } from '../multimodal/ImageAttachmentBar';
import {
  ATTACHMENT_INPUT_ACCEPT,
  MAX_CHAT_IMAGES,
  MAX_IMAGE_SIZE_BYTES,
  readAttachmentDataUrl,
  readingAttachment,
  screenAttachmentFile,
} from '../multimodal/attachments';
import type { ImageAttachment } from '../multimodal/attachments';
import { SlashCommandMenu } from '../chat/SlashCommandMenu';
import { SlashInlineCompletion } from '../chat/SlashInlineCompletion';
import { ModelPickerButton } from '../chat/ModelPickerButton';
import { ThinkingLevelSelect } from '../chat/ThinkingLevelSelect';
import { ChatComposerFooter } from '../chat/ChatComposerFooter';
import { ComposerStatusBar } from '../chat/ComposerStatusBar';
import {
  FALLBACK_COMMANDS,
  completionsFor,
  executeSlashCommand,
  extractCommandHead,
  findCommand,
  resolveCommand,
} from '../chat/slashCommands';
import type { SlashCommandInfo } from '../chat/slashCommands';
import { useAnchoredStore } from '../../store/anchored';
import { setComposerFooterSignal } from './AnchoredStatusRail';
import { AnchoredPopupStack } from './AnchoredPopupStack';
import type { ChatAttachmentPayload } from '../../useChat';
import type { SessionInputKind } from '../../types/chatEvents';
import { useSessionDraft } from '../../hooks/useSessionDraft';
import * as Popover from '@radix-ui/react-popover';
import { api } from '../../api';
import { usePermissionConfig } from '../workspace/usePermissionConfig';
import { PermissionModeToggle } from '../workspace/PermissionModeToggle';
import { PERMISSION_MODE_INFO } from '../workspace/permissionMode';

/** 输入栈整体高度下限：约 64px（一行输入 + 底部操作行 + 内边距）。 */
const STACK_MIN_HEIGHT = 64;
/** 输入栈整体高度上限：240px。 */
const STACK_MAX_HEIGHT = 240;
/** 输入框自身高度上限，给附件条与操作行留出空间。 */
const TEXTAREA_MAX_HEIGHT = 128;
const SLASH_FEEDBACK_MAX_CHARS = 8000;

/**
 * 底部输入栈（高度 64–240px）。自上而下：弹窗栈 → Slash 菜单 → 附件条 →
 * 输入框 + 操作行。弹窗按触发顺序堆叠、最新的在最上层，完成 / 取消后销毁。
 */
export function AnchoredComposer({
  sessionId,
  isStreaming,
  onSend,
  onStop,
  onSubmitInput,
  cwd,
  model,
}: {
  sessionId: string | null;
  isStreaming: boolean;
  onSend: (text: string, images?: string[], files?: ChatAttachmentPayload[]) => void;
  onStop: () => void;
  onSubmitInput?: (text: string, kind: SessionInputKind, requestId: string) => Promise<boolean>;
  /** 状态条展示的工作目录；未上报时留空显示“未上报”。 */
  cwd?: string | null;
  /** 状态条展示的模型名；未上报时留空显示“未上报”。 */
  model?: string | null;
}) {
  const { t } = useI18n();
  const turnTokens = useAnchoredStore((s) => s.turnTokens);
  const permission = usePermissionConfig();
  const [permissionPending, setPermissionPending] = useState(false);
  const permissionLock = useRef(false);
  const [skills, setSkills] = useState<Array<{ id: string; name: string; enabled: boolean | null }>>([]);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [skillsError, setSkillsError] = useState<string | null>(null);
  const [skillPending, setSkillPending] = useState<string | null>(null);
  const skillsLock = useRef(false);
  const { text: input, setText: setInput, storageError } = useSessionDraft(sessionId);
  const [attachments, setAttachments] = useState<ImageAttachment[]>([]);
  const attachmentScope = useMemo(() => ({ sessionId }), [sessionId]);
  const attachmentScopeRef = useRef(attachmentScope);
  attachmentScopeRef.current = attachmentScope;
  const mountedRef = useRef(true);
  const attachmentsRef = useRef(attachments);
  attachmentsRef.current = attachments;
  const [sendSnapshot, setSendSnapshot] = useState<{ text: string; attachments: ImageAttachment[] } | null>(null);
  const changeAttachments = useCallback((next: ImageAttachment[] | ((previous: ImageAttachment[]) => ImageAttachment[])) => {
    if (!mountedRef.current || attachmentScopeRef.current !== attachmentScope) return;
    const value = typeof next === 'function' ? next(attachmentsRef.current) : next;
    attachmentsRef.current = value;
    setAttachments(value);
  }, [attachmentScope]);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);
  const loadSkills = async () => {
    if (skillsLock.current) return;
    skillsLock.current = true;
    setSkillsLoading(true);
    setSkillsError(null);
    try {
      const data = await api.listSkills();
      if (!Array.isArray(data)) throw new Error(t('anchored.composer.skills_bad_format'));
      if (mountedRef.current) setSkills(data.flatMap((row) => {
        if (row.id == null || typeof row.name !== 'string') return [];
        return [{ id: String(row.id), name: row.name, enabled: typeof row.is_enabled === 'boolean' ? row.is_enabled : null }];
      }));
    } catch (cause) {
      if (mountedRef.current) setSkillsError(cause instanceof Error ? cause.message : t('anchored.composer.skills_load_failed'));
    } finally {
      skillsLock.current = false;
      if (mountedRef.current) setSkillsLoading(false);
    }
  };
  const toggleSkill = async (skill: typeof skills[number]) => {
    if (skillsLock.current || skill.enabled === null || isStreaming) return;
    skillsLock.current = true;
    setSkillPending(skill.id);
    setSkillsError(null);
    try {
      const result = await api.toggleSkill(skill.id, !skill.enabled);
      if (typeof result?.is_enabled !== 'boolean') throw new Error(t('anchored.composer.skill_unconfirmed'));
      if (mountedRef.current) setSkills(previous => previous.map(item => item.id === skill.id ? { ...item, enabled: result.is_enabled } : item));
    } catch (cause) {
      if (mountedRef.current) setSkillsError(cause instanceof Error ? cause.message : t('anchored.composer.skill_update_failed'));
    } finally {
      skillsLock.current = false;
      if (mountedRef.current) setSkillPending(null);
    }
  };
  const [slashCatalog, setSlashCatalog] = useState<SlashCommandInfo[]>(FALLBACK_COMMANDS);
  const [slashActiveIndex, setSlashActiveIndex] = useState(0);
  const [slashDismissed, setSlashDismissed] = useState(false);
  /**
   * Debounced instruction understanding shown above the input only when the
   * deterministic pass flags a missing goal or an ambiguity. Mirrors the
   * trace `task_spec`: a plain-language summary plus clarification questions.
   */
  const [clarity, setClarity] = useState<{ summary: string; questions: string[] } | null>(null);
  const [slashFeedback, setSlashFeedback] = useState<{
    command: string; text: string; error: string; status: 'pending' | 'done' | 'error'; streaming: boolean;
  } | null>(null);
  const slashAbortRef = useRef<(() => void) | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const composing = useRef(false);
  const [inputPending, setInputPending] = useState(false);
  const [inputError, setInputError] = useState<string | null>(null);
  const submissionRef = useRef<{ text: string; kind: SessionInputKind; id: string } | null>(null);
  const sessionRef = useRef(sessionId);
  sessionRef.current = sessionId;
  const draftRef = useRef(input);
  draftRef.current = input;
  const submitLock = useRef(false);
  const generationRef = useRef(0);

  // 弹窗栈：输入区上方堆叠，属于输入栈的一部分。
  const popups = useAnchoredStore((s) => s.popups);

  const resizeTextarea = useCallback(() => {
    const node = inputRef.current;
    if (!node) return;
    node.style.height = 'auto';
    node.style.height = `${Math.min(node.scrollHeight, TEXTAREA_MAX_HEIGHT)}px`;
  }, []);

  // 后端目录优先，失败时静默保留本地兜底命令。
  useEffect(() => {
    let active = true;
    api.listChatCommands()
      .then((commands) => {
        if (active && commands?.length) setSlashCatalog(commands as SlashCommandInfo[]);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  const slashHead = extractCommandHead(input);
  useEffect(() => {
    setSlashFeedback(null);
    setAttachments([]);
    attachmentsRef.current = [];
    setSendSnapshot(null);
    setSlashDismissed(false);
    setSlashActiveIndex(0);
    setClarity(null);
    composing.current = false;
    setInputPending(false);
    setInputError(null);
    submissionRef.current = null;
    submitLock.current = false;
    generationRef.current += 1;
    return () => {
      generationRef.current += 1;
      slashAbortRef.current?.();
      slashAbortRef.current = null;
    };
  }, [sessionId]);

  const slashCompletions = useMemo(
    () => (slashHead === null ? [] : completionsFor(slashCatalog, slashHead, isStreaming)),
    [slashCatalog, slashHead, isStreaming],
  );
  const slashMenuVisible = slashHead !== null && !/\s/.test(input.trimStart().slice(1)) && !slashDismissed && slashCompletions.length > 0;
  const selectedSlashIndex = Math.min(slashActiveIndex, Math.max(0, slashCompletions.length - 1));
  const isExactCommand = useCallback((value: string) => resolveCommand(slashCatalog, value) !== null, [slashCatalog]);
  const activeSlashCommand = slashHead === null ? undefined : findCommand(slashCatalog, slashHead);

  const attachmentBlocked = attachments.some(item => item.status !== 'ready' || !item.url);
  const canSubmit = !!input.trim() && !attachmentBlocked && slashFeedback?.status !== 'pending' && (!isStreaming || (activeSlashCommand?.allowed_while_streaming ?? false));
  useEffect(resizeTextarea, [input, resizeTextarea]);

  useEffect(() => {
    const text = input.trim();
    if (text.length < 2 || text.startsWith('/') || isStreaming) {
      setClarity(null);
      return;
    }
    const timer = setTimeout(() => {
      api.understandInstruction(text)
        .then((data) => {
          if (data?.progress !== 'needs_clarification') {
            setClarity(null);
            return;
          }
          const questions = Array.isArray(data.clarification_questions)
            ? data.clarification_questions
            : [];
          setClarity({ summary: data.plain_language_summary ?? '', questions });
        })
        .catch(() => setClarity(null));
    }, 600);
    return () => clearTimeout(timer);
  }, [input, isStreaming]);

  // 把草稿 / 流式状态广播给下方状态栏 footer（同一会话列内协作）。
  useEffect(() => {
    setComposerFooterSignal({ hasDraft: input.trim().length > 0, isStreaming });
  }, [input, isStreaming]);
  useEffect(() => () => {
    setComposerFooterSignal({ hasDraft: false, isStreaming: false });
  }, []);

  const runSlashCommand = useCallback(
    (raw: string) => {
      const command = raw.trim();
      slashAbortRef.current?.();
      slashAbortRef.current = null;
      const streaming = resolveCommand(slashCatalog, command)?.command.streaming ?? false;
      if (!sessionId) {
        setSlashFeedback({ command, text: '', error: '请先选择会话后执行命令。', status: 'error', streaming });
        return;
      }
      const controller = new AbortController();
      setSlashFeedback({ command, text: '', error: '', status: 'pending', streaming });
      const abort = executeSlashCommand(sessionId, command, (event) => {
        if (controller.signal.aborted) return;
        setSlashFeedback((previous) => {
          if (!previous) return previous;
          if (event.type === 'text') return { ...previous, text: (previous.text + event.delta).slice(-SLASH_FEEDBACK_MAX_CHARS) };
          if (event.type === 'error') return { ...previous, error: event.message.slice(0, SLASH_FEEDBACK_MAX_CHARS), status: 'error' };
          if (event.type === 'done') return { ...previous, status: 'done' };
          return previous;
        });
      }, { signal: controller.signal });
      slashAbortRef.current = () => {
        controller.abort();
        abort();
      };
    },
    [sessionId, slashCatalog],
  );

  const submit = useCallback(() => {
    if (!canSubmit) return;
    const text = input.trim();
    if (isExactCommand(text)) {
      runSlashCommand(text);
    } else {
      const ready = attachments.filter((item) => item.status === 'ready' && item.url);
      const images = ready.filter((item) => (item.kind ?? 'image') === 'image').map((item) => item.url);
      const files = ready.map(
        (item): ChatAttachmentPayload => ({
          kind: item.kind ?? 'image',
          data: item.url,
          name: item.name,
          mime_type: item.mimeType ?? 'image/png',
          size: item.size,
        }),
      );
      setSendSnapshot({ text: input, attachments: [...attachments] });
      try {
        if (files.length) onSend(text, images, files);
        else onSend(text);
      } catch (cause) {
        setInputError(cause instanceof Error ? cause.message : '发送回调失败，草稿已保留。');
        return;
      }
      setInputError(null);
      changeAttachments([]);
    }
    setInput('');
    setSlashDismissed(false);
    setSlashActiveIndex(0);
    if (inputRef.current) inputRef.current.style.height = 'auto';
  }, [attachments, canSubmit, input, isExactCommand, onSend, runSlashCommand, setInput, changeAttachments]);

  const submitRunningInput = async (kind: SessionInputKind) => {
    const text = input.trim();
    if (submitLock.current || !sessionId || !onSubmitInput || !text || attachments.length || slashHead !== null) return;
    const previous = submissionRef.current;
    const request = previous?.text === text && previous.kind === kind
      ? previous : { text, kind, id: crypto.randomUUID() };
    submissionRef.current = request;
    const generation = generationRef.current;
    submitLock.current = true;
    setInputPending(true);
    setInputError(null);
    try {
      const confirmed = await onSubmitInput(text, kind, request.id);
      if (sessionRef.current !== sessionId || generation !== generationRef.current) return;
      if (confirmed) {
        if (draftRef.current.trim() === text) setInput('');
        submissionRef.current = null;
      } else setInputError('发送尚未确认，草稿已保留。重试会复用请求标识。');
    } catch (cause) {
      if (sessionRef.current === sessionId && generation === generationRef.current) setInputError(cause instanceof Error ? cause.message : '输入发送失败，草稿已保留。');
    } finally {
      if (sessionRef.current === sessionId && generation === generationRef.current) {
        submitLock.current = false;
        setInputPending(false);
      }
    }
  };
  const canSubmitRunning = !!sessionId && !!onSubmitInput && !!input.trim() && !inputPending && !attachments.length && slashHead === null;

  const handleSelect = useCallback(
    (command: SlashCommandInfo) => {
      setInput(`/${command.name} `);
      setSlashDismissed(true);
      setSlashActiveIndex(0);
      inputRef.current?.focus();
    },
    [setInput],
  );

  const pickAttachment = useCallback(
    async (file: File) => {
      if (!mountedRef.current || attachmentScopeRef.current !== attachmentScope) return;
      const screened = screenAttachmentFile(file, {
        currentCount: attachmentsRef.current.length,
        maxImages: MAX_CHAT_IMAGES,
        maxSizeBytes: MAX_IMAGE_SIZE_BYTES,
        accept: ATTACHMENT_INPUT_ACCEPT,
      });
      if (!screened.ok) { setInputError(screened.rejection.message); return; }
      setInputError(null);
      const placeholder = readingAttachment(file);
      changeAttachments((previous) => [...previous, placeholder]);
      const resolved = await readAttachmentDataUrl(file).catch(() => ({ url: '', status: 'error' as const, error: 'read' as const }));
      changeAttachments((previous) =>
        previous.map((item) => (item.id === placeholder.id ? { ...item, ...resolved } : item)),
      );
    },
    [attachmentScope, changeAttachments],
  );

  return (
    <div
      data-testid="anchored-composer"
      className="codex-composer mx-auto flex w-full max-w-[832px] shrink-0 flex-col gap-[var(--space-2)] bg-[var(--color-bg-page)] px-[var(--space-4)] pb-[var(--space-3)] pt-[var(--space-2)]"
    >
      <AnchoredPopupStack />
      <div data-testid="anchored-composer-surface" className="codex-composer-surface flex flex-col gap-[var(--space-2)] rounded-[var(--radius-xl)] bg-[var(--color-bg-surface-2)] p-[var(--space-3)] transition-shadow focus-within:shadow-[var(--focus-ring)]" style={{ minHeight: STACK_MIN_HEIGHT }}>
      {inputError && <p role="alert" className="text-[length:var(--text-xs)] text-[var(--color-error)]">{inputError}</p>}
      {storageError && <p role="alert" className="text-[length:var(--text-xs)] text-[var(--color-error)]">{storageError}</p>}
      {attachmentBlocked && <p role="alert" className="text-[length:var(--text-xs)] text-[var(--color-text-muted)]">{attachments.some(item => item.status === 'reading') ? t('anchored.composer.attachment_reading') : t('anchored.composer.attachment_failed')}</p>}
      {sendSnapshot && <div className="flex flex-wrap items-center gap-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-muted)]">
        <span>已保留本会话上次发送快照；发送结果请查看聊天区。附件快照仅在当前输入区驻留期间可恢复。</span>
        <Button type="button" size="xs" variant="outline" disabled={!!input || attachments.length > 0 || inputPending} onClick={() => {
          setInput(sendSnapshot.text);
          changeAttachments(sendSnapshot.attachments);
          setSendSnapshot(null);
          inputRef.current?.focus();
        }}>恢复上次发送草稿</Button>
      </div>}

      {slashFeedback && (
        <div
          role={slashFeedback.status === 'error' ? 'alert' : 'status'}
          className="max-h-[var(--space-20)] shrink-0 overflow-y-auto whitespace-pre-wrap break-words rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] p-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-secondary)]"
        >
          <p>{slashFeedback.command.slice(0, SLASH_FEEDBACK_MAX_CHARS)} · {slashFeedback.status === 'pending' ? '等待命令响应' : slashFeedback.status === 'error' ? '命令错误' : '命令响应已结束'}</p>
          {slashFeedback.streaming && <p>流式命令的完整运行详情尚未接入聊天消息流；此处仅显示命令文字与错误。</p>}
          {slashFeedback.text && <p>{slashFeedback.text}</p>}
          {slashFeedback.error && <p className="text-[var(--color-error)]">{slashFeedback.error}</p>}
          {slashFeedback.status === 'error' && (
            <Button
              type="button" size="sm" variant="outline"
              disabled={isStreaming && !(resolveCommand(slashCatalog, slashFeedback.command)?.command.allowed_while_streaming ?? false)}
              onClick={() => runSlashCommand(slashFeedback.command)}
            >重试</Button>
          )}
          <Button type="button" size="sm" variant="outline" onClick={() => {
            slashAbortRef.current?.();
            slashAbortRef.current = null;
            setSlashFeedback(null);
          }}>{slashFeedback.status === 'pending' ? '取消接收' : '关闭'}</Button>
        </div>
      )}

      {clarity && clarity.questions.length > 0 && (
        <div
          role="status"
          className="flex shrink-0 items-start gap-[var(--space-2)] rounded-[var(--radius-md)] border border-[var(--color-warning)]/40 bg-[var(--color-warning-subtle)] p-[var(--space-2)] text-[length:var(--text-xs)]"
        >
          <CircleAlert size={14} aria-hidden="true" className="mt-0.5 shrink-0" />
          <div className="min-w-0 flex-1">
            {clarity.summary && <p className="text-[var(--color-text-secondary)]">{clarity.summary}</p>}
            <p className="mt-0.5 font-medium text-[var(--color-text-primary)]">{t('chat.clarify_hint')}</p>
            <ul className="mt-1 list-inside list-disc space-y-0.5 text-[var(--color-text-secondary)]">
              {clarity.questions.map((question, index) => (
                <li key={index}>{question}</li>
              ))}
            </ul>
          </div>
          <Button type="button" size="xs" variant="ghost" onClick={() => setClarity(null)} className="shrink-0">
            {t('common.dismiss')}
          </Button>
        </div>
      )}

      <div className="relative">
        <SlashCommandMenu
          visible={slashMenuVisible}
          items={slashCompletions}
          activeIndex={selectedSlashIndex}
          onSelect={handleSelect}
          onHover={setSlashActiveIndex}
        />
      </div>

      <ImageAttachmentBar key={sessionId} attachments={attachments} onChange={changeAttachments} onError={(message) => {
        if (mountedRef.current && attachmentScopeRef.current === attachmentScope) setInputError(message);
      }} accept={ATTACHMENT_INPUT_ACCEPT} />

      <div className="relative flex items-end gap-[var(--space-2)]">
        <label
          className="flex size-[var(--control-height-sm)] shrink-0 cursor-pointer items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-3)] hover:text-[var(--color-text-primary)]"
          title={t('chat.attach_image')}
        >
          <Paperclip size={16} aria-hidden="true" />
          <input
            type="file"
            accept={ATTACHMENT_INPUT_ACCEPT}
            multiple
            className="hidden"
            onChange={async (event) => {
              const files = Array.from(event.target.files ?? []);
              event.target.value = '';
              for (const file of files) await pickAttachment(file);
            }}
          />
        </label>

        <span
          aria-hidden="true"
          data-testid="anchored-composer-prompt"
          className="w-[2ch] shrink-0 select-none pb-[var(--space-1-5)] pt-[var(--space-1-5)] text-center font-bold leading-relaxed text-[var(--color-text-secondary)]"
        >
          ›
        </span>

        <textarea
          ref={inputRef}
          value={input}
          rows={1}
          onChange={(event) => {
            setInput(event.target.value);
            setSlashDismissed(false);
            setSlashActiveIndex(0);
            resizeTextarea();
          }}
          onCompositionStart={() => {
            composing.current = true;
          }}
          onCompositionEnd={() => {
            composing.current = false;
          }}
          onKeyDown={(event) => {
            if (composing.current || event.nativeEvent.isComposing || event.keyCode === 229) return;
            if (slashMenuVisible) {
              if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
                event.preventDefault();
                setSlashActiveIndex((selectedSlashIndex + (event.key === 'ArrowDown' ? 1 : -1) + slashCompletions.length) % slashCompletions.length);
                return;
              }
              if (event.key === 'Tab' || (event.key === 'Enter' && !event.shiftKey)) {
                event.preventDefault();
                const selected = slashCompletions[selectedSlashIndex];
                if (selected) handleSelect(selected);
                return;
              }
              if (event.key === 'Escape') {
                event.preventDefault();
                setSlashDismissed(true);
                return;
              }
            }
            if (event.key === 'Enter' && !event.shiftKey && !composing.current) {
              event.preventDefault();
              if (isStreaming && !isExactCommand(input.trim())) void submitRunningInput('steering');
              else submit();
            }
          }}
          placeholder={t('anchored.composer.placeholder', { defaultValue: 'Ask Climber to do anything' })}
          aria-label={t('anchored.composer.placeholder', { defaultValue: 'Ask Climber to do anything' })}
          className="min-w-0 flex-1 resize-none bg-transparent py-[var(--space-1-5)] text-[length:var(--text-sm)] leading-relaxed text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none"
        />

        {slashMenuVisible && (
          <SlashInlineCompletion
            input={input}
            catalog={slashCompletions}
            isStreaming={isStreaming}
            className="absolute bottom-0 pb-[var(--space-1-5)]"
            // The attachment control (control-height-sm) and the 2ch prompt are
            // the two elements between the row's start edge and the textarea,
            // each followed by the row gap; the ghost starts where they end.
            style={{ left: 'calc(var(--control-height-sm) + var(--space-2) + 2ch + var(--space-2))' }}
          />
        )}

        {isStreaming ? (
          <Button type="button" size="sm" variant="outline" onClick={onStop} className="shrink-0">
            <Square size={12} aria-hidden="true" />
            {t('chat.stop')}
          </Button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={!canSubmit}
            aria-label={t('chat.send')}
            title={t('chat.send')}
            className={cn(
              'flex size-8 shrink-0 items-center justify-center rounded-[var(--radius-pill)] transition-colors',
              canSubmit
                ? 'bg-[var(--color-accent-foreground)] text-[var(--color-bg-page)] hover:bg-[var(--color-accent)]'
                : 'cursor-not-allowed bg-[var(--color-bg-surface-3)] text-[var(--color-text-disabled)]',
            )}
          >
            <ArrowUp size={16} aria-hidden="true" />
          </button>
        )}
      </div>

      <div className="flex min-w-0 flex-wrap items-center gap-[var(--space-2)] border-t border-[var(--color-border-subtle)] px-[var(--space-2)] pt-[var(--space-2)]">
        {isStreaming && onSubmitInput && <>
          <Button type="button" size="sm" variant="outline" disabled={!canSubmitRunning} onClick={() => void submitRunningInput('steering')}>{t('anchored.composer.steering_action')}</Button>
          <Button type="button" size="sm" variant="outline" disabled={!canSubmitRunning} onClick={() => void submitRunningInput('follow_up')}>{t('anchored.composer.follow_up_action')}</Button>
          <p role="status" className="text-[length:var(--text-xs)] text-[var(--color-text-muted)]">{inputPending ? t('anchored.composer.pending_ack') : t('anchored.composer.running_submit_hint')}</p>
        </>}
        <ModelPickerButton sessionId={sessionId} disabled={isStreaming} className="max-w-full" />
        <fieldset disabled={isStreaming} className="min-w-0 border-0 p-0 disabled:opacity-60">
          <ThinkingLevelSelect sessionId={sessionId} />
        </fieldset>
        <Popover.Root>
          <Popover.Trigger asChild>
            <Button type="button" variant="ghost" size="xs" aria-label={t('anchored.composer.permission_settings')}>{t('anchored.composer.permission_settings')} · {permissionPending ? t('anchored.composer.pending_confirm') : permission.loading ? t('anchored.composer.loading') : permission.mode ? PERMISSION_MODE_INFO[permission.mode].label : t('anchored.composer.unreported')}</Button>
          </Popover.Trigger>
          <Popover.Portal>
            <Popover.Content side="top" align="start" sideOffset={8} aria-label={t('anchored.composer.permission_settings')} className="z-50 w-80 rounded-[var(--radius-lg)] border border-[var(--color-border-default)] bg-[var(--color-bg-page)] p-[var(--space-3)]">
              <p className="mb-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-muted)]">{t('anchored.composer.global_permission_hint')}</p>
              <PermissionModeToggle value={permission.mode} loading={permission.loading || permissionPending} disabled={isStreaming} error={permission.error} onRetry={permission.reload} onChange={async mode => {
                if (permissionLock.current || isStreaming) return;
                permissionLock.current = true;
                setPermissionPending(true);
                try { await permission.setMode(mode); }
                finally { permissionLock.current = false; if (mountedRef.current) setPermissionPending(false); }
              }} />
            </Popover.Content>
          </Popover.Portal>
        </Popover.Root>
        <Popover.Root onOpenChange={open => { if (open) void loadSkills(); }}>
          <Popover.Trigger asChild><Button type="button" variant="ghost" size="xs">{t('anchored.composer.skills')}</Button></Popover.Trigger>
          <Popover.Portal>
            <Popover.Content side="top" align="start" sideOffset={8} aria-label={t('anchored.composer.skills_catalog_label')} className="z-50 w-80 rounded-[var(--radius-lg)] border border-[var(--color-border-default)] bg-[var(--color-bg-page)] p-[var(--space-3)] text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">
              <p className="mb-[var(--space-2)] text-[var(--color-text-muted)]">{t('anchored.composer.global_skills')}</p>
              {skillsLoading ? <p>{t('anchored.composer.skills_loading')}</p> : <ul className="overflow-y-auto" style={{ maxHeight: STACK_MAX_HEIGHT }}>
                {skills.map(skill => <li key={skill.id} className="flex items-center justify-between gap-[var(--space-2)] py-[var(--space-1)]">
                  <span className="min-w-0 break-words">{skill.name}</span>
                  {skill.enabled === null ? <span>{t('anchored.composer.unreported')}</span> : <button type="button" role="switch" aria-label={skill.name} aria-checked={skill.enabled} disabled={isStreaming || skillPending !== null} onClick={() => void toggleSkill(skill)} className="shrink-0 rounded-[var(--radius-sm)] border border-[var(--color-border-subtle)] px-[var(--space-2)] py-[var(--space-1)] hover:bg-[var(--color-bg-surface-2)] disabled:opacity-50">{skillPending === skill.id ? t('anchored.composer.pending_confirm') : skill.enabled ? t('anchored.composer.enabled') : t('anchored.composer.disabled')}</button>}
                </li>)}
              </ul>}
              {!skillsLoading && skills.length === 0 && !skillsError && <p>{t('anchored.composer.skills_empty')}</p>}
              {skillsError && <p role="alert" className="text-[var(--color-error)]">{skillsError}</p>}
              <div className="mt-[var(--space-2)] flex items-center gap-[var(--space-3)]">
                <Button type="button" variant="ghost" size="xs" disabled={skillsLoading || skillPending !== null} onClick={() => void loadSkills()}>{t('anchored.composer.reload')}</Button>
                <a href="#skills" className="underline">{t('anchored.composer.open_skills_page')}</a>
              </div>
            </Popover.Content>
          </Popover.Portal>
        </Popover.Root>
      </div>
      </div>

      <ComposerStatusBar cwd={cwd} model={model} turnTokens={turnTokens} />
      <ChatComposerFooter hasDraft={input.trim().length > 0} />

      {popups.length > 0 && (
        <p className="sr-only" aria-live="polite">
          {t('anchored.popup.popups_active')}
        </p>
      )}
    </div>
  );
}
