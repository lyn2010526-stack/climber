/**
 * Type-safe translation utilities
 */
import { useTranslation as useBaseT } from 'react-i18next';
import type { SupportedLanguageCode } from './config';

export type TFunction = ReturnType<typeof useBaseT>['t'];

/**
 * Typed translation hook
 */
export function useTypedTranslation<TNamespace extends string = 'translation'>(
  ns?: TNamespace
) {
  const { t, i18n, ready } = useBaseT(ns);

  const changeLanguage = async (lng: SupportedLanguageCode | string) => {
    await i18n.changeLanguage(lng);
    localStorage.setItem('i18next_lng', lng);
  };

  return {
    t: t as TFunction,
    i18n,
    ready,
    changeLanguage,
    currentLanguage: i18n.language,
  };
}

// Helper to define translation namespace types
export type TranslationNamespace = 'translation';
