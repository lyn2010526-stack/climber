export const LOCK_EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];

export const LOCK_ENTRANCE_MS = {
  backdrop: 220,
  revealLineDelay: 80,
  revealLine: 220,
  revealFade: 900,
  brandDelay: 140,
  brandSpring: 420,
  brandOvershoot: 1.04,
  titleDelay: 260,
  title: 260,
  subtitleDelay: 330,
  subtitle: 260,
  dotDelay: 420,
  dotStagger: 40,
  dot: 300,
  keypadDelay: 560,
  keypadSpring: 240,
  faceDelay: 620,
  face: 180,
  hintDelay: 720,
  hint: 200,
} as const;

export const LOCK_UNLOCK_MS = {
  pulse: 80,
  dotStagger: 40,
  dot: 160,
  floatDelay: 280,
  float: 200,
  hold: 500,
  faceFailReset: 260,
  faceCollapse: 240,
} as const;

export const lockSec = (ms: number): number => ms / 1000;
