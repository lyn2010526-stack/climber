import { useTranslation as useBaseTranslation, Trans } from 'react-i18next';
import i18n from './config';
import type { SupportedLanguageCode } from './config';

export function useTranslation(namespace?: string) {
  const { t, i18n, ready } = useBaseTranslation(namespace);
  
  const changeLanguage = async (lng: SupportedLanguageCode | string) => {
    await i18n.changeLanguage(lng);
    localStorage.setItem('i18next_lng', lng);
  };

  const currentLanguage = i18n.language;

  return {
    t,
    i18n,
    ready,
    changeLanguage,
    currentLanguage,
  };
}

export { Trans };

// Hook to get current language code
export function useCurrentLanguage(): string {
  const { i18n } = useBaseTranslation();
  return i18n.language;
}

// Hook for checking if a specific language is active
export function isActiveLanguage(langCode: string): boolean {
  return i18n.language === langCode;
}
