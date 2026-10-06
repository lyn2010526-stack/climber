import { useEffect, useState } from 'react';

const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

export function readPrefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia?.(REDUCED_MOTION_QUERY).matches === true;
}

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(readPrefersReducedMotion);
  useEffect(() => {
    setReduced(readPrefersReducedMotion());
    if (typeof window === 'undefined') return;
    const query = window.matchMedia?.(REDUCED_MOTION_QUERY);
    if (!query) return;
    const listener = () => setReduced(readPrefersReducedMotion());
    query.addEventListener('change', listener);
    return () => {
      query.removeEventListener('change', listener);
    };
  }, []);
  return reduced;
}
