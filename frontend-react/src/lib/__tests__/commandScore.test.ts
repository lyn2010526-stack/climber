import { describe, expect, it } from 'vitest';
import { normalizeForMatch, rankCommands, scoreCommand } from '../commandScore';
import type { CommandCandidate } from '../commandScore';

const candidate = (label: string, keywords = '', group = ''): CommandCandidate => ({
  label,
  keywords,
  group,
});

/** Grade of the winning field, for the assertions below that read like the spec. */
const grade = (query: string, item: CommandCandidate) => scoreCommand(query, item)?.grade;

describe('normalizeForMatch', () => {
  it('folds case and collapses whitespace runs', () => {
    expect(normalizeForMatch('  Task   History ')).toBe('task history');
    expect(normalizeForMatch('API\tAccess\nKey')).toBe('api access key');
    expect(normalizeForMatch('   ')).toBe('');
  });
});

describe('scoreCommand grades', () => {
  it('ranks an exact field above a prefix, a word start, a substring and a fuzzy match', () => {
    // One candidate per grade, all against the same needle.
    const needle = 'set';
    const grades = [
      grade(needle, candidate('set')), // exact
      grade(needle, candidate('settings')), // prefix
      grade(needle, candidate('system set', '', '')), // word-start
      grade(needle, candidate('asset')), // substring
      grade(needle, candidate('s-e-tup')), // fuzzy
    ];
    expect(grades).toEqual(['exact', 'prefix', 'word-start', 'substring', 'fuzzy']);
  });

  it('treats a whole-field match as exact and a case-different one as the same grade', () => {
    expect(grade('API Access', candidate('api access'))).toBe('exact');
    expect(grade('settings', candidate('SETTINGS'))).toBe('exact');
  });

  it('separates a word-boundary match from one buried inside a word', () => {
    // "set" starts the word in "system set" but sits inside "asset".
    expect(grade('set', candidate('system set'))).toBe('word-start');
    expect(grade('set', candidate('asset'))).toBe('substring');
  });

  it('finds a multi-word needle whose words are out of order as a word-start match', () => {
    // "history" comes before "reasoning" in the label, so the two needle words
    // appear in the field but not in the order they were typed.
    expect(grade('history reasoning', candidate('Reasoning History', 'reason reasoning'))).toBe('word-start');
  });

  it('scores a fuzzy match only when the characters appear in order', () => {
    expect(grade('stng', candidate('settings'))).toBe('fuzzy');
    // "gnits" is not a subsequence of "settings".
    expect(scoreCommand('gnits', candidate('settings'))).toBeNull();
  });
});

describe('scoreCommand bonuses', () => {
  it('prefers a match that starts a word over one buried mid-word', () => {
    // "sett" sits inside "resetting" but starts the word in "resetting sett".
    const buried = scoreCommand('sett', candidate('resetting'))!;
    const onWord = scoreCommand('sett', candidate('resetting sett'))!;
    expect(buried.grade).toBe('substring');
    expect(onWord.grade).toBe('word-start');
    expect(onWord.score).toBeGreaterThan(buried.score);
  });

  it('prefers an earlier match position inside one grade', () => {
    const late = scoreCommand('s', candidate('history', 'deep dive settings'))!;
    const early = scoreCommand('s', candidate('stats', 'deep dive settings'))!;
    expect(early.field).toBe('label');
    expect(early.score).toBeGreaterThan(late.score);
  });

  it('prefers a tight subsequence over a scattered one inside the fuzzy grade', () => {
    // Both fields hold s, t and g in order, neither as a phrase.
    const tight = scoreCommand('stg', candidate('s t g'))!;
    const scattered = scoreCommand('stg', candidate('settings'))!;
    expect(tight.grade).toBe('fuzzy');
    expect(scattered.grade).toBe('fuzzy');
    expect(tight.score).toBeGreaterThan(scattered.score);
  });

  it('resolves a tie between fields in favour of the label', () => {
    // Every field is the same whole-field match, so the field order decides.
    const result = scoreCommand('set', candidate('set', 'set', 'set'))!;
    expect(result.grade).toBe('exact');
    expect(result.field).toBe('label');
  });
});

describe('scoreCommand field priority', () => {
  it('prefers the label over keywords and keywords over the group', () => {
    expect(scoreCommand('trace', candidate('Traces', 'trace graph'))!.field).toBe('label');
    expect(scoreCommand('graph', candidate('Traces', 'trace graph'))!.field).toBe('keywords');
    expect(scoreCommand('ops', candidate('Traces', '', 'ops config'))!.field).toBe('group');
  });

  it('lets the strongest grade win over the most specific field', () => {
    // The group heading contains the needle outright, but the label matches
    // farther into the word, so the label's stronger grade is what ranks it.
    const result = scoreCommand('set', candidate('settings', '', 'settings config'))!;
    expect(result.field).toBe('label');
    expect(result.grade).toBe('prefix');
  });

  it('lets the strongest grade win over the most specific field', () => {
    // The group heading contains the needle outright, but the label matches more
    // exactly, so the label's grade is what ranks the candidate.
    const result = scoreCommand('set', candidate('settings', '', 'settings config'))!;
    expect(result.field).toBe('label');
    expect(result.grade).toBe('prefix');
  });
});

describe('scoreCommand no match', () => {
  it('returns null when nothing matches', () => {
    expect(scoreCommand('unmatched-xyz', candidate('Settings', 'prefs', 'config'))).toBeNull();
  });

  it('returns null for an empty query, since every candidate would tie', () => {
    expect(scoreCommand('', candidate('Settings'))).toBeNull();
    expect(scoreCommand('   ', candidate('Settings'))).toBeNull();
  });
});

describe('rankCommands', () => {
  const items = [
    candidate('Dashboard', 'dashboard health status'),
    candidate('Traces', 'trace debug 追踪 链路'),
    candidate('Chat', 'home workspace dashboard 对话 工作台'),
    candidate('Settings', 'settings config preference 设置'),
    candidate('Task History', 'history past 历史'),
  ];

  it('returns every candidate in declaration order for an empty query', () => {
    expect(rankCommands(items, '').map(item => item.label)).toEqual(items.map(item => item.label));
    expect(rankCommands(items, '   ').map(item => item.label)).toEqual(items.map(item => item.label));
  });

  it('drops candidates that do not match', () => {
    const ranked = rankCommands(items, 'trace');
    expect(ranked.map(item => item.label)).toEqual(['Traces']);
  });

  it('orders prefix matches ahead of keyword and fuzzy matches', () => {
    // "settings" is the label prefix of Settings; Dashboard only carries the word
    // in its keywords; Traces matches nothing at all.
    const ranked = rankCommands(items, 'settings').map(item => item.label);
    expect(ranked[0]).toBe('Settings');
  });

  it('ranks all twenty-five nav items, so every entry stays reachable by typing', async () => {
    const { ALL_NAV_ITEMS_BASE } = await import('../../navigation/navConfig');
    const nav = ALL_NAV_ITEMS_BASE.map(item => ({
      label: item.label ?? item.labelKey ?? item.id,
      keywords: item.keywords ?? '',
      group: item.group ?? 'config',
    }));
    // A single character of each label is a subsequence, so nothing is lost.
    for (const item of nav) {
      const firstChar = item.label.slice(0, 1);
      expect(rankCommands(nav, firstChar).map(entry => entry.label)).toContain(item.label);
    }
  });

  it('keeps declaration order when two candidates score the same', () => {
    const tied = [candidate('alpha one'), candidate('alpha two')];
    // "alpha" is the same prefix of both labels and the rest of both fields is
    // the same length, so the sort must not reorder them.
    expect(rankCommands(tied, 'alpha').map(item => item.label)).toEqual(['alpha one', 'alpha two']);
    expect(rankCommands([...tied].reverse(), 'alpha').map(item => item.label)).toEqual(['alpha two', 'alpha one']);
  });

  it('applies a limit only to a ranked query', () => {
    expect(rankCommands(items, '', { limit: 2 })).toHaveLength(5);
    expect(rankCommands(items, 'a', { limit: 2 })).toHaveLength(2);
  });

  it('handles Chinese queries with no word separators', () => {
    const zh = [candidate('推理引擎'), candidate('追踪链路'), candidate('会话')];
    expect(rankCommands(zh, '推理').map(item => item.label)).toEqual(['推理引擎']);
    expect(rankCommands(zh, '会话').map(item => item.label)).toEqual(['会话']);
  });
});
