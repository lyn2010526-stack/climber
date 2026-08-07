import i18n from 'i18next';
import type { InitOptions } from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import enTranslation from '../../public/locales/en.json';
import zhCNTranslation from '../../public/locales/zh-CN.json';
import jaTranslation from '../../public/locales/ja.json';
import koTranslation from '../../public/locales/ko.json';
import esTranslation from '../../public/locales/es.json';
import frTranslation from '../../public/locales/fr.json';
import deTranslation from '../../public/locales/de.json';

export const supportedLanguages = [
  { code: 'en', name: 'English', flag: '🇺🇸', rtl: false },
  { code: 'zh-CN', name: '中文（简体）', flag: '🇨🇳', rtl: false },
  { code: 'ja', name: '日本語', flag: '🇯🇵', rtl: false },
  { code: 'ko', name: '한국어', flag: '🇰🇷', rtl: false },
  { code: 'es', name: 'Español', flag: '🇪🇸', rtl: false },
  { code: 'fr', name: 'Français', flag: '🇫🇷', rtl: false },
  { code: 'de', name: 'Deutsch', flag: '🇩🇪', rtl: false },
] as const;

export type SupportedLanguageCode = (typeof supportedLanguages)[number]['code'];

export const languages = supportedLanguages.map((lang) => lang.code);

const i18nOptions: InitOptions = {
  resources: {
    'en': { translation: enTranslation },
    'zh-CN': { translation: zhCNTranslation },
    'ja': { translation: jaTranslation },
    'ko': { translation: koTranslation },
    'es': { translation: esTranslation },
    'fr': { translation: frTranslation },
    'de': { translation: deTranslation },
  },
  fallbackLng: 'en',
  debug: false,
  interpolation: {
    escapeValue: false,
  },
  detection: {
    order: ['localStorage', 'navigator', 'htmlTag'],
    lookupLocalStorage: 'i18next_lng',
    caches: ['localStorage'],
  },
  compatibilityJSON: 'v4',
  ns: ['translation'],
  defaultNS: 'translation',
  returnNull: false,
  saveMissing: false,
  pluralSeparator: '_',
  contextSeparator: '_',
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init(i18nOptions);

const detectedLanguage = i18n.language;
localStorage.setItem('i18next_lng', detectedLanguage);

export default i18n;
