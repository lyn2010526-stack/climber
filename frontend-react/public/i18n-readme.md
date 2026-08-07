# Internationalization (i18n) System

Complete internationalization support for Agent Engine with 5 languages: English, Chinese (Simplified), Japanese, Korean, and Spanish.

## Features

- ✅ **5 Supported Languages**: English (en), Chinese Simplified (zh-CN), Japanese (ja), Korean (ko), Spanish (es)
- ✅ **Automatic Language Detection**: Detects browser language automatically
- ✅ **Persistent Preferences**: Saves user language preference in localStorage
- ✅ **Easy Language Switching**: UI dropdown component with instant switching
- ✅ **Type Safety**: TypeScript interfaces for all translation keys
- ✅ **Fallback Support**: Graceful fallback to English if translation missing
- ✅ **React Integration**: Seamless `react-i18next` integration

## Installation

Dependencies are already installed:

```bash
npm install react-i18next i18next i18next-browser-languagedetector
```

## Configuration

### Basic Setup

The i18n configuration is located at `/src/i18n/config.ts`:

```typescript
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      'en': { translation: enTranslation },
      'zh-CN': { translation: zhCNTranslation },
      'ja': { translation: jaTranslation },
      'ko': { translation: koTranslation },
      'es': { translation: esTranslation },
    },
    fallbackLng: 'en',
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'i18next_lng',
    },
  });
```

### Adding New Languages

1. Create new locale file in `/public/locales/{code}.json`
2. Update `/src/i18n/config.ts` to add the new language
3. Export supported languages array

## Usage

### 1. Using Translation Hook

```tsx
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation();

  return <h1>{t('common.welcome')}</h1>;
}
```

### 2. With Namespaces

```tsx
const { t } = useTranslation('translation'); // or custom namespace
return <p>{t('navigation.dashboard')}</p>;
```

### 3. Language Switching

```tsx
import { useTranslation } from 'react-i18next';

function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  
  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
    localStorage.setItem('i18next_lng', lng);
  };

  return (
    <select onChange={(e) => changeLanguage(e.target.value)}>
      <option value="en">English</option>
      <option value="zh-CN">中文</option>
      <option value="ja">日本語</option>
      <option value="ko">한국어</option>
      <option value="es">Español</option>
    </select>
  );
}
```

### 4. Pre-built LanguageSwitcher Component

```tsx
import { LanguageSwitcher } from '@/components/LanguageSwitcher';

<MyComponent>
  <LanguageSwitcher className="my-custom-class" />
</MyComponent>
```

### 5. Translations with Parameters

```tsx
// JSON file
{
  "greeting": "Hello, {{name}}!",
  "itemCount": "{{count}} items found"
}

// Usage
<t>
  Hello, {{name: 'John'}}!
</t>
<t count={5}>
  {{count}} items found
</t>
```

### 6. Translation Types

```tsx
import type { RootJson } from '@/i18n/types';
import type { TFunction } from 'react-i18next';

const { t }: TFunction<RootJson> = useTranslation();
```

## File Structure

```
frontend-react/
├── public/
│   └── locales/
│       ├── en.json        # English translations
│       ├── zh-CN.json     # Chinese (Simplified)
│       ├── ja.json        # Japanese
│       ├── ko.json        # Korean
│       └── es.json        # Spanish
└── src/
    ├── i18n/
    │   ├── config.ts      # i18n configuration
    │   ├── hooks.ts       # Custom hooks
    │   ├── types.ts       # TypeScript interfaces
    │   ├── utils.ts       # Utility functions
    │   └── typed.ts       # Type-safe utilities
    └── components/
        └── LanguageSwitcher.tsx  # Language switcher component
```

## Available Hooks & Utilities

### `useTranslation()`

Standard react-i18next hook.

### `useI18n(namespace?)`

Extended hook with additional utilities:

```typescript
const { 
  t,                // Translation function
  i18n,             // i18n instance
  ready,            // Loading state
  changeLanguage,   // Function to change language
  currentLanguage,  // Current language code
  isRTL,            // RTL direction flag
  supportedLanguages  // List of supported languages
} = useI18n();
```

### `formatDate()`, `formatNumber()`, `formatRelativeTime()`

Locale-aware formatting utilities:

```typescript
import { formatDate, formatNumber, formatRelativeTime } from '@/i18n/utils';

const date = new Date();
const localizedDate = formatDate(date, { year: 'numeric', month: 'long' });
const price = formatNumber(1234.56);
const timeAgo = formatRelativeTime('2024-01-15T10:30:00Z');
```

## Common Patterns

### Pattern 1: Static Text

```tsx
// Good - Use translation key
<h1>{t('home.title')}</h1>

// Bad - Hardcoded text
<h1>Dashboard</h1>
```

### Pattern 2: Dynamic Values

```tsx
// With interpolation
<p>{t('agents.agent_created')}!</p>

// With parameters
<p>{t('analytics.unique_visitors')}: {visitorCount}</p>
```

### Pattern 3: Conditional Content

```tsx
const isActive = true;
<div>
  {isActive ? t('status.active') : t('status.inactive')}
</div>
```

## Migration Guide

### Before

```tsx
import React from 'react';

export function DashboardPage() {
  return (
    <div>
      <h1>Dashboard</h1>
      <p>Welcome back!</p>
      <button>Save</button>
    </div>
  );
}
```

### After

```tsx
import React from 'react';
import { useTranslation } from 'react-i18next';

export function DashboardPage() {
  const { t } = useTranslation();

  return (
    <div>
      <h1>{t('home.title')}</h1>
      <p>{t('home.welcome_message')}</p>
      <button>{t('common.save')}</button>
    </div>
  );
}
```

## Best Practices

1. ✅ Use descriptive keys: `auth.login_title` not `lt`
2. ✅ Group related keys by category
3. ✅ Keep translations short and contextual
4. ✅ Use parameters for dynamic values, not concatenation
5. ✅ Don't translate HTML tags, use `<Trans>` component
6. ✅ Always include translations in components
7. ✅ Test all languages before deployment

## Troubleshooting

### Issue: Translations not loading

**Solution**: Check that `./i18n/config.ts` is imported in `main.tsx`

### Issue: Wrong language showing

**Solution**: Clear localStorage and reload page

### Issue: Missing translation warnings

**Solution**: Add missing keys to translation files with fallback to English

## Adding Translations to Pages

See the migration guide in individual pages for examples. Key pages include:

- `DashboardPage.tsx`
- `LoginPage.tsx`
- `SettingsPage.tsx`
- `AgentsPage.tsx`
- `ChatPage.tsx`

## Maintenance

### Updating Existing Translations

1. Find translation keys in translation files
2. Update the translation text for each language
3. Test changes in browser

### Removing Unused Keys

1. Search codebase for unused translation keys
2. Remove from all language files
3. Run lint checks

## Testing

```tsx
import { render, screen } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from './i18n/config';

test('renders translated text', () => {
  render(
    <I18nextProvider i18n={i18n}>
      <MyComponent />
    </I18nextProvider>
  );
  expect(screen.getByText(/welcome/i)).toBeInTheDocument();
});
```

## References

- [i18next Documentation](https://www.i18next.com/)
- [react-i18next Documentation](https://react.i18next.com/)
- [i18next Browser Language Detector](https://github.com/i18next/i18next-browser-languagedetector)
