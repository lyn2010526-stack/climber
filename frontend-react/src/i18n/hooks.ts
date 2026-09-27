import { useI18n } from './utils';

/**
 * Back-compat alias. The app standardised on `useI18n` (see ./utils); this
 * re-export keeps existing call sites working without a second implementation
 * drifting out of sync.
 */
export const useTranslation = useI18n;

export { Trans, isActiveLanguage } from './utils';

export function useCurrentLanguage(): string {
  return useI18n().currentLanguage;
}
