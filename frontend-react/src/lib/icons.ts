import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  CircleDashed,
  Eye,
  EyeOff,
  FileX,
  Hourglass,
  Inbox,
  Info,
  Loader2,
  LockKeyhole,
  Moon,
  Search,
  ShieldQuestion,
  Sun,
  X,
  type LucideIcon,
  type LucideProps,
} from 'lucide-react';
import { createElement, forwardRef } from 'react';
import { WorkbenchIcon } from '../components/ui/WorkbenchIcon';

const WorkbenchSettings = forwardRef<SVGSVGElement, LucideProps>((props, ref) =>
  createElement(WorkbenchIcon, { ...props, ref, name: 'settings', size: Number(props.size ?? 16) }),
);

/**
 * The only four icon sizes the design system ships. Anything outside this
 * ladder reads as noise, so controls pick the closest rung instead of
 * inventing per-call overrides.
 */
export const iconSizes = { xs: 12, sm: 14, md: 16, lg: 20 } as const;

export type IconSizeName = keyof typeof iconSizes;

/**
 * Shared-control meanings, named by intent rather than by glyph shape. A call
 * site asks for the meaning it is reporting; picking the drawing is this table's
 * job, so a glyph swap never reaches a component.
 *
 * Every key is named here because the shared control layer actually draws it.
 * The two status states an agent workbench needs on top of the four outcomes
 * and the plain "no status" case are `queued` (accepted, not started) and
 * `approval` (blocked on a decision from the user); both are rendered by
 * `StatusIcon`, which is the single tone-to-glyph entry point.
 */
export const icons = {
  // Status: outcomes first, then the two states that are not outcomes.
  error: AlertCircle,
  success: CheckCircle2,
  warning: AlertTriangle,
  info: Info,
  loading: Loader2,
  /** Accepted and waiting for a slot. Motion marks `loading`, so a queue entry
   *  needs a static glyph of its own to stay readable with reduced motion on. */
  queued: Hourglass,
  /** A tool call parked on a human decision, the one state a run cannot leave
   *  by itself. */
  approval: ShieldQuestion,
  /** A value the backend never reported. Distinct from `loading` and from an
   *  inactive control, so a missing field never reads as pending or healthy. */
  unknown: CircleDashed,
  // Control affordances.
  showPassword: Eye,
  hidePassword: EyeOff,
  close: X,
  settings: WorkbenchSettings,
  privacyLock: LockKeyhole,
  submenu: ChevronRight,
  // Empty states.
  emptyInbox: Inbox,
  emptySearch: Search,
  emptyFile: FileX,
  // Theme.
  lightTheme: Sun,
  darkTheme: Moon,
} as const satisfies Record<string, LucideIcon>;

export type SemanticIconName = keyof typeof icons;

/** The status vocabulary, as data so nothing has to retype the list. */
export const statusTones = [
  'error',
  'success',
  'warning',
  'info',
  'loading',
  'queued',
  'approval',
  'unknown',
] as const;

export type StatusTone = (typeof statusTones)[number];

/**
 * The semantic name each tone reports. Kept as names rather than components so
 * a caller that only needs to know the state does not have to import a glyph;
 * `StatusIcon` owns the drawing and reads this table for the name.
 */
const statusIconName = {
  error: 'error',
  success: 'success',
  warning: 'warning',
  info: 'info',
  loading: 'loading',
  queued: 'queued',
  approval: 'approval',
  unknown: 'unknown',
} as const satisfies Record<StatusTone, SemanticIconName>;

/**
 * Status colors exist to communicate state and nothing else, so this is the
 * single place a control may reach for them. A control with no status resolves
 * to no icon at all rather than to a neutral placeholder, so an absent state and
 * a healthy one can never look the same.
 */
export function statusIconFor(tone?: StatusTone | null): SemanticIconName | null {
  return tone ? statusIconName[tone] ?? null : null;
}

/** Numeric size for an icon name, clamped to the four-rung ladder. */
export function iconSize(size?: IconSizeName): number {
  return iconSizes[size ?? 'md'] ?? iconSizes.md;
}
