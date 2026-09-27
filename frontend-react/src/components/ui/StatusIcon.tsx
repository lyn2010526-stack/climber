import type { LucideIcon } from 'lucide-react';
import { icons, iconSizes, type IconSizeName, type StatusTone } from '../../lib/icons';
import { cn } from '../../lib/utils';

/**
 * The one place a control turns a tone into a glyph. Every tone is named here
 * against the semantic table rather than resolved by lookup, so a new tone
 * cannot join `StatusTone` without this map answering for it, and
 * `designTokens.test.ts` reads the two tables side by side to prove they agree.
 */
const TONE_GLYPH: Record<StatusTone, LucideIcon> = {
  error: icons.error,
  success: icons.success,
  warning: icons.warning,
  info: icons.info,
  loading: icons.loading,
  queued: icons.queued,
  approval: icons.approval,
  unknown: icons.unknown,
};

/**
 * Tone to text colour, and the only status colours in the shared layer. Every
 * value is a `--color-*` token, so a status follows the theme instead of
 * carrying a fixed hue: an outcome takes its own role, `queued` takes the
 * disabled text so a waiting run stays quieter than a running one, and
 * `approval` takes the accent because the workbench is waiting on the user.
 */
const TONE_TEXT: Record<StatusTone, string> = {
  error: 'text-[var(--color-error)]',
  success: 'text-[var(--color-success)]',
  warning: 'text-[var(--color-warning)]',
  info: 'text-[var(--color-info)]',
  loading: 'text-[var(--color-text-muted)]',
  queued: 'text-[var(--color-text-disabled)]',
  approval: 'text-[var(--color-accent)]',
  unknown: 'text-[var(--color-unknown)]',
};

export interface StatusIconProps {
  /** Omit it, or pass `null`, when the control carries no status. */
  tone?: StatusTone | null;
  size?: IconSizeName;
  /**
   * Motion is the running status's own cue, so it is on for `loading` and off
   * for every other tone. Set it to `false` to still a loading glyph inside
   * motion-sensitive surroundings.
   */
  spin?: boolean;
  className?: string;
}

/**
 * Status is carried by the label as well as the glyph, so every instance stays
 * decorative for assistive technology and the tone colour is never the only
 * carrier of meaning. The glyph itself takes its colour from the surrounding
 * text through `currentColor`; nothing here paints the drawing.
 */
export function StatusIcon({ tone, size = 'md', spin, className }: StatusIconProps) {
  if (!tone) return null;
  const Glyph = TONE_GLYPH[tone];
  const spinning = tone === 'loading' && spin !== false;
  return (
    <Glyph
      size={iconSizes[size]}
      className={cn('shrink-0', TONE_TEXT[tone], spinning && 'animate-spin motion-reduce:animate-none', className)}
      aria-hidden="true"
      focusable="false"
    />
  );
}

export { TONE_GLYPH, TONE_TEXT };
