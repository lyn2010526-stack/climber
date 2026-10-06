import { cn } from '../../lib/utils';

/**
 * Ported from codex `tui/src/shimmer.rs` (`shimmer_spans`). Codex sweeps a
 * highlight across the text once per ~2.0s (`sweep_seconds = 2.0`,
 * `band_half_width = 5` chars), blending a dim base colour into a bright band.
 * The web port reproduces that sweep with a background gradient clipped to the
 * glyphs; the gradient and the 2s period live in the stylesheet next to the
 * existing `shimmer` keyframe, and reduced motion collapses it to static text.
 *
 * Codex returns nothing for empty input, so an empty string renders nothing.
 */
export interface ShimmerTextProps {
  text: string;
  className?: string;
}

export function ShimmerText({ text, className }: ShimmerTextProps) {
  if (text.length === 0) return null;
  return (
    <span className={cn('codex-shimmer-text', className)}>{text}</span>
  );
}
