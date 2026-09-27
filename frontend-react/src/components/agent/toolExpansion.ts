import { useStoredFlag } from './readingWidth';

/** Persisted preference: tool cards open themselves when they carry content. */
export const AUTO_EXPAND_TOOLS_KEY = 'climber.chat.autoExpandTools';

/**
 * Whether tool cards expand themselves by default.
 *
 * Persisted like every other user preference and off by default, so a run's
 * tool output only spreads out when the user asked for it.
 */
export function useAutoExpandTools(): [boolean, () => void] {
  return useStoredFlag(AUTO_EXPAND_TOOLS_KEY);
}
