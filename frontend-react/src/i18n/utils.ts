import { useTranslation as useBaseT, Trans } from 'react-i18next';
import i18n from './config';
import type { SupportedLanguageCode } from './config';

/**
 * Hook for translation with additional utilities
 */
export function useI18n(namespace?: string) {
  const { t, i18n, ready } = useBaseT(namespace);
  
  const changeLanguage = async (lng: SupportedLanguageCode | string) => {
    await i18n.changeLanguage(lng);
    localStorage.setItem('i18next_lng', lng);
  };

  const currentLanguage = i18n.language;
  const isRTL = ['ar', 'he', 'fa', 'ur'].includes(currentLanguage);

  return {
    t,
    i18n,
    ready,
    changeLanguage,
    currentLanguage,
    isRTL,
    supportedLanguages: i18n.languages,
  };
}

/**
 * Get current language code
 */
export function getCurrentLanguage(): string {
  return i18n.language;
}

/**
 * Check if specific language is active
 */
export function isActiveLanguage(code: string): boolean {
  return i18n.language === code;
}

/**
 * Format date with current locale
 */
export function formatDate(date: Date | string | number, options?: Intl.DateTimeFormatOptions): string {
  const d = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  return new Intl.DateTimeFormat(i18n.language, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...options,
  }).format(d);
}

/**
 * Format time with current locale
 */
export function formatTime(date: Date | string | number, options?: Intl.DateTimeFormatOptions): string {
  const d = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  return new Intl.DateTimeFormat(i18n.language, {
    hour: '2-digit',
    minute: '2-digit',
    ...options,
  }).format(d);
}

/**
 * Format date and time with current locale
 */
export function formatDateTime(date: Date | string | number, options?: Intl.DateTimeFormatOptions): string {
  const d = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  return new Intl.DateTimeFormat(i18n.language, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    ...options,
  }).format(d);
}

/**
 * Format number with current locale
 */
export function formatNumber(
  num: number,
  options?: Intl.NumberFormatOptions
): string {
  return new Intl.NumberFormat(i18n.language, options).format(num);
}

/**
 * Format currency with current locale
 */
export function formatCurrency(
  amount: number,
  currency: string = 'USD',
  options?: Intl.NumberFormatOptions
): string {
  return new Intl.NumberFormat(i18n.language, {
    style: 'currency',
    currency,
    ...options,
  }).format(amount);
}

/**
 * Format percentage with current locale
 */
export function formatPercent(
  num: number,
  options?: Intl.NumberFormatOptions
): string {
  return new Intl.NumberFormat(i18n.language, {
    style: 'percent',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
    ...options,
  }).format(num);
}

/**
 * Format file size with current locale
 */
export function formatFileSize(bytes: number): string {
  
  if (bytes === 0) return formatNumber(0) + ' B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return formatNumber(parseFloat((bytes / Math.pow(k, i)).toFixed(2)), {
    maximumFractionDigits: 2,
  }) + ' ' + sizes[i];
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: Date | string | number): string {
  const d = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffSecs = Math.round(diffMs / 1000);
  const diffMins = Math.round(diffMs / 60000);
  const diffHours = Math.round(diffMs / 3600000);
  const diffDays = Math.round(diffMs / 86400000);

  const rtf = new Intl.RelativeTimeFormat(i18n.language, { numeric: 'auto' });

  if (diffSecs < 60) return rtf.format(-diffSecs, 'second');
  if (diffMins < 60) return rtf.format(-diffMins, 'minute');
  if (diffHours < 24) return rtf.format(-diffHours, 'hour');
  if (diffDays < 7) return rtf.format(-diffDays, 'day');
  if (diffDays < 30) return rtf.format(-Math.round(diffDays / 7), 'week');
  if (diffDays < 365) return rtf.format(-Math.round(diffDays / 30), 'month');
  
  return rtf.format(-Math.round(diffDays / 365), 'year');
}

/**
 * Format ordinal number with current locale
 */
export function formatOrdinal(num: number): string {
  const pr = new Intl.PluralRules(i18n.language, { type: 'ordinal' });
  const suffixes = new Map([
    ['one', 'st'],
    ['two', 'nd'],
    ['few', 'rd'],
    ['other', 'th'],
  ]);
  const rule = pr.select(num);
  const suffix = suffixes.get(rule) || 'th';
  return formatNumber(num) + suffix;
}

export { Trans };
