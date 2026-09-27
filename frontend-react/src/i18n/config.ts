import i18n from 'i18next';
import type { InitOptions } from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import enTranslation from '../locales/en.json';
import zhCNTranslation from '../locales/zh-CN.json';
import jaTranslation from '../locales/ja.json';
import koTranslation from '../locales/ko.json';
import esTranslation from '../locales/es.json';
import frTranslation from '../locales/fr.json';
import deTranslation from '../locales/de.json';

export const supportedLanguages = [
  { code: 'en', name: 'English', rtl: false },
  { code: 'zh-CN', name: '中文（简体）', rtl: false },
  { code: 'ja', name: '日本語', rtl: false },
  { code: 'ko', name: '한국어', rtl: false },
  { code: 'es', name: 'Español', rtl: false },
  { code: 'fr', name: 'Français', rtl: false },
  { code: 'de', name: 'Deutsch', rtl: false },
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
  fallbackLng: 'zh-CN',
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
