/**
 * Explainable command matching, in the shape fzf and cmdk use: a grade says how
 * a candidate matched and a score says how well, so two candidates that both
 * matched can still be ordered. cmdk's `defaultFilter` returns 1 for an exact
 * match and roughly 0.9 for a prefix (lobe-chat depends on that band when it
 * pins server-ranked results to a constant), which a boolean `includes` cannot
 * express.
 *
 * The strongest grade a candidate achieves across its fields wins, and the score
 * only orders candidates that reached the same grade. `scoreCommand` returns null
 * for a candidate with no match at all, and `rankCommands` drops those.
 */

export const MATCH_GRADES = ['exact', 'prefix', 'word-start', 'substring', 'fuzzy'] as const;
export type MatchGrade = (typeof MATCH_GRADES)[number];

/**
 * Each grade carries a rank (smaller is stronger, so the best field can be picked)
 * and a score band base. The bands are far enough apart that a grade always beats
 * any amount of in-grade tuning from a weaker match.
 */
const GRADE: Record<MatchGrade, { rank: number; base: number }> = {
  exact: { rank: 0, base: 1000 },
  prefix: { rank: 1, base: 800 },
  'word-start': { rank: 2, base: 600 },
  substring: { rank: 3, base: 400 },
  fuzzy: { rank: 4, base: 200 },
};

/** Fields in the order the user means them: the label is what they read, the
 *  keywords and the group heading are what they might have meant instead. */
export type ScoredField = 'label' | 'keywords' | 'group';
const FIELDS: readonly ScoredField[] = ['label', 'keywords', 'group'];

const BONUS_CONSECUTIVE = 8;
const BONUS_WORD_START = 6;
const EARLIEST_POSITION = 6;
/** Keeps a long label from winning on match position alone. */
const LENGTH_PENALTY_DIVISOR = 20;
/** A needle spread across the whole field is weaker than a tight one. */
const GAP_PENALTY_DIVISOR = 4;

/** Case folds, and every whitespace run collapses to a single separator. */
const SEPARATOR = ' ';

export function normalizeForMatch(value: string): string {
  return value.toLowerCase().replace(/\s+/g, SEPARATOR).trim();
}

const isSeparator = (char: string | undefined) => char === SEPARATOR;

/** True when `index` starts a word: it is the first character or follows a separator. */
function isWordStart(haystack: string, index: number): boolean {
  return index === 0 || isSeparator(haystack[index - 1]);
}

/** The needle is one phrase; a needle of only separators matches nothing. */
function needleTokens(needle: string): string[] {
  return needle.split(SEPARATOR).filter(token => token.length > 0);
}

interface Run {
  index: number;
  length: number;
}

/**
 * Pick the tightest occurrence. When several exist, a word-boundary occurrence
 * beats an earlier one buried mid-word: "settings" typed against the keywords
 * "dashboard settings" is about the word settings, not the "e" inside "dashboard".
 * Among equally good occurrences the earlier one wins.
 */
function locate(needle: string, haystack: string): Run | null {
  const first = haystack.indexOf(needle);
  if (first < 0) return null;
  if (isWordStart(haystack, first)) return { index: first, length: needle.length };

  const wordStart = haystack.indexOf(SEPARATOR + needle);
  return wordStart < 0
    ? { index: first, length: needle.length }
    : { index: wordStart + 1, length: needle.length };
}

/** The tightest window holding the whole subsequence, greedy from every start. */
function tightestRun(chars: readonly string[], haystack: string): Run | null {
  let best: Run | null = null;
  for (let start = 0; start < haystack.length; start += 1) {
    if (haystack[start] !== chars[0]) continue;
    let cursor = start;
    for (const char of chars) {
      cursor = haystack.indexOf(char, cursor);
      if (cursor < 0) break;
      cursor += 1;
    }
    if (cursor < 0) continue;
    const run = { index: start, length: cursor - start };
    if (!best || run.length < best.length) best = run;
  }
  return best;
}

interface FieldMatch {
  grade: MatchGrade;
  /** The span the user sees highlighted. */
  run: Run;
  /** Longest run of needle characters found back to back; 0 for contiguous matches. */
  consecutive: number;
  /** Needle characters that had to be skipped inside `run`. */
  gaps: number;
  wordStart: boolean;
}

/** Longest back-to-back run of `chars` inside `run`, walking forward from it. */
function longestConsecutive(chars: readonly string[], haystack: string, run: Run): number {
  let longest = 0;
  let current = 0;
  let cursor = run.index;
  for (const char of chars) {
    if (haystack[cursor] === char) {
      current += 1;
      if (current > longest) longest = current;
      cursor += 1;
    } else {
      current = 0;
      cursor = haystack.indexOf(char, cursor);
      if (cursor < 0) break;
    }
  }
  return longest;
}

/**
 * Grade one field against the needle. Returns null when the field cannot match,
 * which lets the caller move on to the next field or exclude the candidate.
 */
function matchField(needle: string, haystack: string): FieldMatch | null {
  if (!needle || !haystack) return null;

  if (haystack === needle) {
    // The field is nothing but the query.
    return { grade: 'exact', run: { index: 0, length: haystack.length }, consecutive: 0, gaps: 0, wordStart: true };
  }

  const direct = locate(needle, haystack);
  if (direct) {
    // A phrase touching the first character is a prefix; the same phrase
    // touching a later word boundary is a word-start match.
    const grade: MatchGrade = direct.index === 0 ? 'prefix' : isWordStart(haystack, direct.index) ? 'word-start' : 'substring';
    return { grade, run: direct, consecutive: 0, gaps: 0, wordStart: isWordStart(haystack, direct.index) };
  }

  // The phrase can be absent as a whole while every one of its words is present,
  // as in "task history" against the keywords "history past".
  const tokens = needleTokens(needle);
  if (tokens.length > 1) {
    const runs: Run[] = [];
    for (const token of tokens) {
      const run = locate(token, haystack);
      if (!run) break;
      runs.push(run);
    }
    if (runs.length === tokens.length) {
      const first = runs[0]!;
      const last = runs[runs.length - 1]!;
      return {
        grade: 'word-start',
        run: { index: first.index, length: last.index + last.length - first.index },
        consecutive: 0,
        gaps: needle.length - tokens.reduce((sum, token) => sum + token.length, 0),
        wordStart: runs.every(run => isWordStart(haystack, run.index)),
      };
    }
  }

  const chars = [...needle.replaceAll(SEPARATOR, '')];
  const run = tightestRun(chars, haystack);
  if (!run) return null;

  return {
    grade: 'fuzzy',
    run,
    consecutive: longestConsecutive(chars, haystack, run),
    gaps: run.length - chars.length,
    wordStart: isWordStart(haystack, run.index),
  };
}

/**
 * Order candidates inside one grade band: earlier match position, a match on a
 * word boundary, and a tight or long run all raise the score; a long field
 * lowers it.
 */
function fieldScore(needle: string, haystack: string, match: FieldMatch): number {
  const lengthPenalty = Math.floor(haystack.length / LENGTH_PENALTY_DIVISOR);
  if (match.grade === 'exact') {
    // A field that is nothing but the query is the strongest match available;
    // among exact matches the shorter field is the more direct answer.
    return -lengthPenalty;
  }

  const wordStart = match.wordStart ? BONUS_WORD_START : 0;
  const earliness = EARLIEST_POSITION - Math.min(match.run.index, EARLIEST_POSITION);
  const gapPenalty = Math.floor(match.gaps / GAP_PENALTY_DIVISOR);
  // A contiguous match has no gaps and a run as long as the needle.
  const matchedLength = Math.max(match.consecutive, needle.length - gapPenalty);
  const tightness = Math.max(0, BONUS_CONSECUTIVE * matchedLength - gapPenalty);

  return earliness + wordStart + tightness - lengthPenalty;
}

export interface CommandCandidate {
  label: string;
  keywords: string;
  group: string;
}

export interface ScoredCommand {
  score: number;
  grade: MatchGrade;
  /** The field that produced the winning grade. */
  field: ScoredField;
}

/**
 * Score one candidate against one query.
 *
 * The strongest grade across the fields wins outright, so a group heading that
 * happens to contain the query cannot outrank a command the user named outright.
 * Inside one grade the match quality decides, and a genuine tie falls to the field
 * order, so among equally exact matches the label wins. The returned score is the
 * grade band plus that quality, which is what `rankCommands` sorts on.
 */
export function scoreCommand(query: string, candidate: CommandCandidate): ScoredCommand | null {
  const needle = normalizeForMatch(query);
  if (!needle) return null;

  let best: ScoredCommand | null = null;
  let bestRank = Number.MAX_SAFE_INTEGER;
  let bestQuality = Number.NEGATIVE_INFINITY;

  for (const field of FIELDS) {
    const haystack = normalizeForMatch(candidate[field]);
    if (!haystack) continue;

    const match = matchField(needle, haystack);
    if (!match) continue;

    const { rank, base } = GRADE[match.grade];
    if (rank > bestRank) continue;

    const quality = fieldScore(needle, haystack, match);
    const beats = rank < bestRank || (rank === bestRank && quality > bestQuality);
    if (beats) {
      bestRank = rank;
      bestQuality = quality;
      best = { grade: match.grade, field, score: base + quality };
    }
  }

  return best;
}

export interface RankCommandsOptions {
  /** How many ranked rows to keep. */
  limit?: number;
}

/**
 * Score every candidate, drop the ones that do not match, and sort best first.
 * `Array.prototype.sort` is stable, so equal scores keep declaration order, which
 * is how the palette keeps nav-config order among equally good matches.
 */
export function rankCommands<T extends CommandCandidate>(
  items: readonly T[],
  query: string,
  options: RankCommandsOptions = {},
): T[] {
  if (!normalizeForMatch(query)) return items.slice();

  const scored: { item: T; score: number }[] = [];
  for (const item of items) {
    const result = scoreCommand(query, item);
    if (result) scored.push({ item, score: result.score });
  }
  scored.sort((a, b) => b.score - a.score);

  const ranked = scored.map(entry => entry.item);
  return options.limit === undefined ? ranked : ranked.slice(0, options.limit);
}
