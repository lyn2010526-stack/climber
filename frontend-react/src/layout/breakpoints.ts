import { useEffect, useState } from 'react';

export const DESKTOP_MIN = 768;
export const COMPACT_DESKTOP_MAX = 1023;
export const FULL_DESKTOP = 1024;
export const WIDE_DESKTOP = 1280;

export function useMediaQuery(query: string): boolean {
  const read = () => window.matchMedia(query).matches;
  const [matches, setMatches] = useState(read);

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, [query]);

  return matches;
}

export function useIsMobile(): boolean {
  return useMediaQuery(`(max-width: ${DESKTOP_MIN - 1}px)`);
}

export function useIsCompactDesktop(): boolean {
  return useMediaQuery(`(min-width: ${DESKTOP_MIN}px) and (max-width: ${COMPACT_DESKTOP_MAX}px)`);
}

export function useIsFullDesktop(): boolean {
  return useMediaQuery(`(min-width: ${FULL_DESKTOP}px)`);
}

export function useIsWideDesktop(): boolean {
  return useMediaQuery(`(min-width: ${WIDE_DESKTOP}px)`);
}
