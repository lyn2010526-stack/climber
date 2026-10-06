import { useSyncExternalStore } from 'react';
import type { TypewriterPreset } from '../../hooks/useTypewriterReveal';

export type TypewriterMode = 'off' | TypewriterPreset;

export const TYPEWRITER_MODE_ORDER: readonly TypewriterMode[] = ['off', 'balanced', 'realtime', 'silky'];

const STORAGE_KEY = 'climber.anchored.typewriter-mode';
const DEFAULT_MODE: TypewriterMode = 'off';

function isTypewriterMode(value: unknown): value is TypewriterMode {
  return typeof value === 'string' && (TYPEWRITER_MODE_ORDER as readonly string[]).includes(value);
}

function readStoredMode(): TypewriterMode {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return isTypewriterMode(raw) ? raw : DEFAULT_MODE;
  } catch {
    return DEFAULT_MODE;
  }
}

let mode: TypewriterMode = typeof localStorage === 'undefined' ? DEFAULT_MODE : readStoredMode();
const listeners = new Set<() => void>();

export function getTypewriterMode(): TypewriterMode {
  return mode;
}

export function subscribeTypewriterMode(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Persist a mode and notify subscribers without touching the app-wide pinned store. */
export function setTypewriterMode(next: TypewriterMode): void {
  mode = next;
  try {
    localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // Storage can be disabled; the in-memory mode still applies.
  }
  for (const listener of listeners) listener();
}

/** Advance to the next preset; returns the newly active mode. */
export function cycleTypewriterMode(): TypewriterMode {
  const index = TYPEWRITER_MODE_ORDER.indexOf(mode);
  const next = TYPEWRITER_MODE_ORDER[(index + 1) % TYPEWRITER_MODE_ORDER.length] ?? DEFAULT_MODE;
  setTypewriterMode(next);
  return next;
}

export function isTypewriterActive(selected: TypewriterMode): boolean {
  return selected !== 'off';
}

export function useTypewriterMode(): TypewriterMode {
  return useSyncExternalStore(subscribeTypewriterMode, getTypewriterMode, getTypewriterMode);
}

/** Resolve the reveal preset for a mode; 'off' is never an active preset. */
export function typewriterPresetFor(selected: TypewriterMode): TypewriterPreset {
  return selected === 'off' ? 'balanced' : selected;
}