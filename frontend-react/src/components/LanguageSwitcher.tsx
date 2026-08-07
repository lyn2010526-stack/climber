import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { supportedLanguages, SupportedLanguageCode } from '../i18n/config';
import { cn } from '../lib/utils';

interface LanguageSwitcherProps {
  className?: string;
  showFlag?: boolean;
  compact?: boolean;
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({ 
  className,
  showFlag = false,
  compact = false 
}) => {
  const { i18n, t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentLang = supportedLanguages.find(
    (lang) => lang.code === i18n.language
  ) || supportedLanguages[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLanguageChange = async (langCode: SupportedLanguageCode) => {
    await i18n.changeLanguage(langCode);
    localStorage.setItem('i18next_lng', langCode);
    document.documentElement.lang = langCode;
    document.documentElement.dir = supportedLanguages.find(l => l.code === langCode)?.rtl ? 'rtl' : 'ltr';
    setIsOpen(false);
  };

  return (
    <div ref={dropdownRef} className={cn('relative inline-block', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors',
          compact ? 'px-2 py-1' : 'px-3 py-2'
        )}
        aria-haspopup="true"
        aria-expanded={isOpen}
        aria-label={t('user_menu.language_settings')}
      >
        {showFlag && (
          <span className="text-base" role="img" aria-label={currentLang.name}>
            {currentLang.flag}
          </span>
        )}
        <span className={cn('font-medium', compact ? 'text-xs' : 'text-sm')}>
          {currentLang.name}
        </span>
        <svg
          className={cn(
            'transition-transform',
            compact ? 'w-3 h-3' : 'w-4 h-4',
            isOpen ? 'rotate-180' : ''
          )}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <div 
          className={cn(
            'absolute mt-2 rounded-lg shadow-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 z-50 overflow-hidden',
            compact ? 'right-0 w-36' : 'right-0 w-48'
          )}
        >
          <div className="py-1">
            <div className={cn(
              'font-semibold text-gray-500 dark:text-gray-400 uppercase',
              compact ? 'px-3 py-1.5 text-[10px]' : 'px-4 py-2 text-xs'
            )}>
              {t('user_menu.language_settings')}
            </div>
            {supportedLanguages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => handleLanguageChange(lang.code)}
                className={cn(
                  'w-full text-left flex items-center justify-between transition-colors',
                  compact ? 'px-3 py-1.5 text-xs' : 'px-4 py-2 text-sm',
                  'hover:bg-gray-100 dark:hover:bg-gray-700',
                  currentLang.code === lang.code 
                    ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' 
                    : 'text-gray-700 dark:text-gray-300'
                )}
              >
                <span className="flex items-center gap-2">
                  {showFlag && <span>{lang.flag}</span>}
                  <span>{lang.name}</span>
                </span>
                {currentLang.code === lang.code && (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default LanguageSwitcher;
