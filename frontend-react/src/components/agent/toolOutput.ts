/**
 * Outputs longer than this are clipped until the user asks for the rest.
 *
 * A tool that returns a whole file would otherwise push every other row off
 * screen. The length reported to the reader stays the real one, so the offer to
 * read more is never a guess.
 */
export const RESULT_PREVIEW_LIMIT = 10000;

export interface OutputSelection {
  /** What to render: the whole output, or its first `RESULT_PREVIEW_LIMIT` characters. */
  text: string;
  /** Whether `text` is a clip of a longer output. */
  truncated: boolean;
  /** The output's real length, clipped or not. */
  fullLength: number;
}

/**
 * Choose how much of an output to show.
 *
 * @param output The tool's output, exactly as the backend reported it.
 * @param showAll Whether the reader already asked for the untruncated text.
 */
export function selectOutputText(output: string, showAll: boolean): OutputSelection {
  const fullLength = output.length;
  const truncated = fullLength > RESULT_PREVIEW_LIMIT && !showAll;
  return { text: truncated ? output.slice(0, RESULT_PREVIEW_LIMIT) : output, truncated, fullLength };
}
