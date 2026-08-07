"""
Backend i18n support using Python's built-in gettext module.
Provides translation utilities for server-side rendering and API responses.
"""

import gettext
import os
from pathlib import Path
from typing import Optional, Dict, Any

LOCALES_DIR = Path(__file__).parent.parent / "locales"
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ["en", "zh_CN", "ja", "ko", "es", "fr", "de"]

# In-memory cache for translation objects
_translations_cache: Dict[str, gettext.GNUTranslations] = {}


def get_translation(language: str, domain: str = "messages") -> gettext.GNUTranslations:
    """
    Get translation object for a given language.
    
    Args:
        language: Language code (e.g., 'en', 'zh_CN', 'ja')
        domain: Translation domain name
        
    Returns:
        GNUTranslations object for the language
    """
    cache_key = f"{language}_{domain}"
    
    if cache_key in _translations_cache:
        return _translations_cache[cache_key]
    
    try:
        translation = gettext.translation(
            domain,
            localedir=str(LOCALES_DIR),
            languages=[language],
            fallback=True
        )
        _translations_cache[cache_key] = translation
        return translation
    except Exception:
        return gettext.NullTranslations()


def translate(text: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """
    Translate a text string to the specified language.
    
    Args:
        text: The text to translate
        language: Target language code
        **kwargs: Variables for string formatting
        
    Returns:
        Translated text (or original if no translation found)
    """
    if language == DEFAULT_LANGUAGE and not kwargs:
        return text
    
    translation = get_translation(language)
    translated = translation.gettext(text)
    
    if kwargs:
        try:
            translated = translated.format(**kwargs)
        except (KeyError, IndexError):
            pass
    
    return translated


def ngettext(singular: str, plural: str, n: int, language: str = DEFAULT_LANGUAGE) -> str:
    """
    Translate a text with plural forms.
    
    Args:
        singular: Singular form
        plural: Plural form
        n: Count
        language: Target language code
        
    Returns:
        Translated text with correct plural form
    """
    translation = get_translation(language)
    return translation.ngettext(singular, plural, n)


def get_language_from_header(header: Optional[str]) -> str:
    """
    Parse Accept-Language header and return best matching language.
    
    Args:
        header: Accept-Language header value
        
    Returns:
        Best matching language code
    """
    if not header:
        return DEFAULT_LANGUAGE
    
    languages = []
    for lang_entry in header.split(","):
        parts = lang_entry.strip().split(";q=")
        lang = parts[0].strip()
        quality = float(parts[1]) if len(parts) > 1 else 1.0
        languages.append((lang, quality))
    
    languages.sort(key=lambda x: x[1], reverse=True)
    
    for lang, _ in languages:
        lang_lower = lang.lower().replace("-", "_")
        
        for supported in SUPPORTED_LANGUAGES:
            if lang_lower == supported.lower():
                return supported
        
        base_lang = lang_lower.split("_")[0]
        for supported in SUPPORTED_LANGUAGES:
            if supported.lower().startswith(base_lang):
                return supported
    
    return DEFAULT_LANGUAGE


def format_datetime(dt: Any, language: str = DEFAULT_LANGUAGE, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """
    Format datetime according to locale conventions.
    
    Args:
        dt: datetime object
        language: Language code
        fmt: Format string
        
    Returns:
        Formatted datetime string
    """
    if dt is None:
        return ""
    
    from datetime import datetime
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except (ValueError, TypeError):
            return dt
    
    return dt.strftime(fmt)


def format_number(num: float, language: str = DEFAULT_LANGUAGE, decimal_places: int = 2) -> str:
    """
    Format number according to locale conventions.
    
    Args:
        num: Number to format
        language: Language code
        decimal_places: Number of decimal places
        
    Returns:
        Formatted number string
    """
    try:
        return f"{num:,.{decimal_places}f}"
    except (ValueError, TypeError):
        return str(num)


def format_currency(amount: float, language: str = DEFAULT_LANGUAGE, currency: str = "USD") -> str:
    """
    Format currency according to locale conventions.
    
    Args:
        amount: Amount to format
        language: Language code
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "KRW": "₩",
        "CNY": "¥",
    }
    symbol = symbols.get(currency, currency)
    
    formatted = format_number(amount, language)
    
    if language in ["en"]:
        return f"{symbol}{formatted}"
    else:
        return f"{formatted} {symbol}"


def clear_cache():
    """Clear the translation cache."""
    _translations_cache.clear()


class TranslationContext:
    """
    Context manager for setting translation language in a block.
    
    Usage:
        with TranslationContext("ja"):
            text = translate("Hello")
    """
    
    def __init__(self, language: str = DEFAULT_LANGUAGE):
        self.language = language
    
    def gettext(self, text: str, **kwargs) -> str:
        return translate(text, self.language, **kwargs)
    
    def ngettext(self, singular: str, plural: str, n: int) -> str:
        return ngettext(singular, plural, n, self.language)
