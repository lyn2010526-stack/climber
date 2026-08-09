#!/usr/bin/env python3
"""
Add a new language to the i18n system.
Creates a new locale file based on the English reference.
"""

import json
import sys
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "public" / "locales"
REFERENCE_LANG = "en"

def load_json(filepath: Path) -> dict:
    """Load JSON file."""
    with open(filepath, encoding='utf-8') as f:
        return json.load(f)

def save_json(filepath: Path, data: dict):
    """Save JSON file with proper formatting."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')

def create_template(reference: dict) -> dict:
    """Create a template with empty values for translation."""
    template = {}
    for key, value in reference.items():
        if isinstance(value, dict):
            template[key] = create_template(value)
        else:
            template[key] = ""
    return template

def add_language(code: str, name: str):
    """Add a new language file."""
    reference_file = LOCALES_DIR / f"{REFERENCE_LANG}.json"
    new_file = LOCALES_DIR / f"{code}.json"

    if not reference_file.exists():
        print(f"Error: Reference file {reference_file} not found")
        sys.exit(1)

    if new_file.exists():
        print(f"Warning: {new_file} already exists. Overwrite? (y/N)")
        response = input().strip().lower()
        if response != 'y':
            print("Aborted.")
            sys.exit(0)

    reference = load_json(reference_file)
    template = create_template(reference)

    save_json(new_file, template)

    print(f"\n✓ Created {new_file}")
    print("\nNext steps:")
    print(f"  1. Translate all empty strings in {code}.json")
    print("  2. Add the language to frontend-react/src/i18n/config.ts:")
    print(f"     {{ code: '{code}', name: '{name}', flag: '🏳️', rtl: false }},")
    print("  3. Run 'npm run i18n:check' to verify completeness")

def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python3 add-language.py <code> <name>")
        print("Example: python3 add-language.py pt-BR 'Português (Brasil)'")
        sys.exit(1)

    code = sys.argv[1]
    name = sys.argv[2]

    if not LOCALES_DIR.exists():
        print(f"Error: Locales directory {LOCALES_DIR} not found")
        sys.exit(1)

    add_language(code, name)

if __name__ == "__main__":
    main()
