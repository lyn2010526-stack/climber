import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import i18n from '../../i18n';
import { FALLBACK_COMMANDS } from './slashCommands';
import { SlashInlineCompletion } from './SlashInlineCompletion';
import { inlineSlashCompletion } from './slashInline';

beforeEach(async () => {
  await i18n.changeLanguage('zh-CN');
});

afterEach(() => {
  document.body.innerHTML = '';
});

describe('inlineSlashCompletion — 纯函数', () => {
  it('回填命令名的剩余字符，并保留已输入的前缀', () => {
    const completion = inlineSlashCompletion('/mo', FALLBACK_COMMANDS);
    expect(completion).not.toBeNull();
    expect(completion?.typed).toBe('/mo');
    expect(completion?.suffix).toBe('del');
    expect(completion?.command.name).toBe('model');
  });

  it('按字母序在多个候选中取第一个', () => {
    // status / stop 都以 s 开头，排序后 status 在前。
    expect(inlineSlashCompletion('/s', FALLBACK_COMMANDS)?.command.name).toBe('status');
  });

  it('一旦出现空格（进入参数区）就不再有内联补全', () => {
    expect(inlineSlashCompletion('/model gpt', FALLBACK_COMMANDS)).toBeNull();
  });

  it('裸斜杠与无匹配时不补全', () => {
    expect(inlineSlashCompletion('/', FALLBACK_COMMANDS)).toBeNull();
    expect(inlineSlashCompletion('/zzz', FALLBACK_COMMANDS)).toBeNull();
  });

  it('已经完整输入命令名时不再显示幽灵补全', () => {
    expect(inlineSlashCompletion('/model', FALLBACK_COMMANDS)).toBeNull();
  });

  it('流式期间只补全能在此期间执行的命令', () => {
    // status 不允许流式调用，stop 允许。
    expect(inlineSlashCompletion('/s', FALLBACK_COMMANDS)?.command.name).toBe('status');
    expect(inlineSlashCompletion('/s', FALLBACK_COMMANDS, true)?.command.name).toBe('stop');
  });

  it('大小写不敏感', () => {
    expect(inlineSlashCompletion('/MO', FALLBACK_COMMANDS)?.suffix).toBe('del');
  });
});

describe('SlashInlineCompletion — 幽灵文本', () => {
  it('渲染已输入的不可见前缀与可见的补全后缀', () => {
    render(<SlashInlineCompletion input="/mo" catalog={FALLBACK_COMMANDS} />);
    const ghost = screen.getByTestId('slash-inline-completion');
    expect(ghost).toHaveAttribute('aria-hidden', 'true');
    expect(ghost).toHaveAttribute('data-command', 'model');
    expect(ghost.textContent).toContain('model');
    // 已输入部分只占位，不重复显示。
    expect(ghost.querySelector('.invisible')?.textContent).toBe('/mo');
  });

  it('带上 Tab 补全提示（i18n defaultValue 回退）', () => {
    render(<SlashInlineCompletion input="/re" catalog={FALLBACK_COMMANDS} />);
    expect(screen.getByTestId('slash-inline-completion').textContent).toContain('Tab');
  });

  it('没有可补全内容时不渲染', () => {
    render(<SlashInlineCompletion input="/model done" catalog={FALLBACK_COMMANDS} />);
    expect(screen.queryByTestId('slash-inline-completion')).toBeNull();
  });
});
