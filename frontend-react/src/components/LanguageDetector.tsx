import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { supportedLanguages } from '../i18n/config';

export const LanguageDetector = () => {
  const { i18n } = useTranslation();

  useEffect(() => {
    const savedLang = localStorage.getItem('i18next_lng');
    
    if (savedLang && i18n.languages.includes(savedLang)) {
      i18n.changeLanguage(savedLang);
    } else {
      const browserLang = navigator.language;
      const matchedLang = supportedLanguages.find(
        lang => browserLang.startsWith(lang.code) || lang.code.startsWith(browserLang)
      );
      
      if (matchedLang) {
        i18n.changeLanguage(matchedLang.code);
        localStorage.setItem('i18next_lng', matchedLang.code);
      }
    }
  }, [i18n]);

  useEffect(() => {
    const currentLang = supportedLanguages.find(l => l.code === i18n.language);
    document.documentElement.lang = i18n.language;
    document.documentElement.dir = currentLang?.rtl ? 'rtl' : 'ltr';
  }, [i18n.language]);

  return null;
};

export default LanguageDetector;
