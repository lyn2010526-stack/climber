#!/usr/bin/env python3
"""
Extract translation keys from TypeScript/TSX source files.
Scans the codebase for t() function calls and generates a list of used keys.
"""

import json
import re
import sys
from pathlib import Path

SRC_DIR = Path(__file__).parent.parent / "src"
LOCALES_DIR = Path(__file__).parent.parent / "public" / "locales"

# Patterns to match translation key usage
PATTERNS = [
    # t('key') or t("key")
    r"""\bt\(\s*['"]([^'"]+)['"]""",
    # t('key', { ... }) or t("key", { ... })
    r"""\bt\(\s*['"]([^'"]+)['"]\s*,""",
    # Trans component
    r"""<Trans\s+i18nKey=['"]([^'"]+)['"]""",
    # useTranslation with key
    r"""i18nKey=['"]([^'"]+)['"]""",
]

def extract_keys_from_file(filepath: Path) -> set[str]:
    """Extract translation keys from a single file."""
    keys = set()
    try:
        content = filepath.read_text(encoding='utf-8')
        for pattern in PATTERNS:
            matches = re.findall(pattern, content)
            keys.update(matches)
    except Exception:
        pass
    return keys

def extract_all_keys() -> set[str]:
    """Extract all translation keys from source files."""
    all_keys = set()

    for ext in ['*.ts', '*.tsx']:
        for filepath in SRC_DIR.rglob(ext):
            if 'node_modules' not in str(filepath):
                keys = extract_keys_from_file(filepath)
                all_keys.update(keys)

    return all_keys

def get_locale_keys() -> set[str]:
    """Get all keys from the English locale file."""
    en_file = LOCALES_DIR / "en.json"
    if not en_file.exists():
        return set()

    def get_nested_keys(d, prefix=""):
        keys = set()
        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                keys.update(get_nested_keys(value, full_key))
            else:
                keys.add(full_key)
        return keys

    with open(en_file, encoding='utf-8') as f:
        data = json.load(f)

    return get_nested_keys(data)

def main():
    """Main entry point."""
    print("Extracting translation keys from source files...\n")

    used_keys = extract_all_keys()
    locale_keys = get_locale_keys()

    # Find unused keys (in locale but not in code)
    unused_keys = locale_keys - used_keys

    # Find missing keys (in code but not in locale)
    missing_keys = used_keys - locale_keys

    print(f"Keys found in source code: {len(used_keys)}")
    print(f"Keys in locale files:      {len(locale_keys)}")
    print()

    if missing_keys:
        print(f"⚠ Keys used in code but missing from locale ({len(missing_keys)}):")
        for key in sorted(missing_keys):
            print(f"  - {key}")
        print()

    if unused_keys:
        print(f"ℹ Keys in locale but not found in code ({len(unused_keys)}):")
        for key in sorted(unused_keys)[:20]:
            print(f"  - {key}")
        if len(unused_keys) > 20:
            print(f"  ... and {len(unused_keys) - 20} more")
        print()

    if not missing_keys and not unused_keys:
        print("✓ All keys are in sync!")

    # Output JSON for CI integration
    if '--json' in sys.argv:
        result = {
            "used_keys": sorted(used_keys),
            "locale_keys": sorted(locale_keys),
            "missing_keys": sorted(missing_keys),
            "unused_keys": sorted(unused_keys),
        }
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
