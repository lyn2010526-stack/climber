/**
 * Type-safe translation utilities.
 *
 * Thin alias over `useI18n` (./utils) so the app has a single implementation.
 * Kept so existing "typed" naming / imports stay valid.
 */
export { useI18n as useTypedTranslation } from './utils';

export type TFunction = ReturnType<typeof import('react-i18next').useTranslation>['t'];

// Helper to define translation namespace types
export type TranslationNamespace = 'translation';
