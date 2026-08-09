#!/usr/bin/env python3
"""
Translation completeness check script.
Compares all locale files against the English reference (en.json).
Reports missing keys, extra keys, and translation coverage statistics.
"""

import json
import sys
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "public" / "locales"
REFERENCE_LANG = "en"

def load_json(filepath: Path) -> dict:
    """Load JSON file and return its contents."""
    try:
        with open(filepath, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return {}

def get_nested_keys(d: dict, prefix: str = "") -> set[str]:
    """Get all nested keys from a dictionary as dotted paths."""
    keys = set()
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(get_nested_keys(value, full_key))
        else:
            keys.add(full_key)
    return keys

def get_nested_value(d: dict, key_path: str) -> any:
    """Get value from nested dictionary using dotted key path."""
    keys = key_path.split(".")
    current = d
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current

def check_translations() -> tuple[bool, dict]:
    """Check all translations against the reference language."""
    reference_file = LOCALES_DIR / f"{REFERENCE_LANG}.json"

    if not reference_file.exists():
        print(f"Error: Reference file {reference_file} not found")
        return False, {}

    reference = load_json(reference_file)
    reference_keys = get_nested_keys(reference)

    results = {
        "reference": REFERENCE_LANG,
        "reference_key_count": len(reference_keys),
        "languages": {},
        "summary": {
            "total_missing": 0,
            "total_extra": 0,
            "incomplete": [],
            "complete": [],
        }
    }

    locale_files = sorted(LOCALES_DIR.glob("*.json"))

    for locale_file in locale_files:
        lang = locale_file.stem
        if lang == REFERENCE_LANG:
            continue

        translation = load_json(locale_file)
        translation_keys = get_nested_keys(translation)

        missing_keys = reference_keys - translation_keys
        extra_keys = translation_keys - reference_keys

        # Check for empty translations
        empty_keys = set()
        for key in translation_keys & reference_keys:
            value = get_nested_value(translation, key)
            if value is None or (isinstance(value, str) and not value.strip()):
                empty_keys.add(key)

        actual_coverage = (len(translation_keys & reference_keys) - len(empty_keys)) / len(reference_keys) * 100 if reference_keys else 0

        lang_result = {
            "total_keys": len(translation_keys),
            "missing_keys": sorted(missing_keys),
            "extra_keys": sorted(extra_keys),
            "empty_keys": sorted(empty_keys),
            "missing_count": len(missing_keys),
            "extra_count": len(extra_keys),
            "empty_count": len(empty_keys),
            "coverage": round(actual_coverage, 1),
            "is_complete": len(missing_keys) == 0 and len(empty_keys) == 0,
        }

        results["languages"][lang] = lang_result
        results["summary"]["total_missing"] += len(missing_keys)
        results["summary"]["total_extra"] += len(extra_keys)

        if lang_result["is_complete"]:
            results["summary"]["complete"].append(lang)
        else:
            results["summary"]["incomplete"].append(lang)

    is_ok = len(results["summary"]["incomplete"]) == 0 and results["summary"]["total_missing"] == 0
    return is_ok, results

def print_report(results: dict):
    """Print a formatted report of translation completeness."""
    print("=" * 70)
    print("TRANSLATION COMPLETENESS REPORT")
    print("=" * 70)
    print(f"\nReference: {results['reference']} ({results['reference_key_count']} keys)\n")

    for lang, data in sorted(results["languages"].items()):
        status = "✓ COMPLETE" if data["is_complete"] else "✗ INCOMPLETE"
        print(f"{lang:8} | {status:12} | Coverage: {data['coverage']:5.1f}% | Keys: {data['total_keys']:3}")

        if data["missing_keys"]:
            print(f"         | Missing keys ({data['missing_count']}):")
            for key in data["missing_keys"][:10]:
                print(f"           - {key}")
            if data["missing_count"] > 10:
                print(f"           ... and {data['missing_count'] - 10} more")

        if data["empty_keys"]:
            print(f"         | Empty translations ({data['empty_count']}):")
            for key in data["empty_keys"][:5]:
                print(f"           - {key}")
            if data["empty_count"] > 5:
                print(f"           ... and {data['empty_count'] - 5} more")

        if data["extra_keys"]:
            print(f"         | Extra keys ({data['extra_count']}):")
            for key in data["extra_keys"][:3]:
                print(f"           + {key}")
            if data["extra_count"] > 3:
                print(f"           ... and {data['extra_count'] - 3} more")

        print()

    print("-" * 70)
    print("SUMMARY")
    print("-" * 70)
    print(f"Languages checked:  {len(results['languages'])}")
    print(f"Complete:           {len(results['summary']['complete'])}")
    print(f"Incomplete:         {len(results['summary']['incomplete'])}")
    print(f"Total missing keys: {results['summary']['total_missing']}")
    print(f"Total extra keys:   {results['summary']['total_extra']}")
    print("=" * 70)

def main():
    """Main entry point."""
    print("Checking translation completeness...\n")

    if not LOCALES_DIR.exists():
        print(f"Error: Locales directory {LOCALES_DIR} not found")
        sys.exit(1)

    is_complete, results = check_translations()

    if not results:
        sys.exit(1)

    print_report(results)

    if not is_complete:
        print("\n⚠ Some translations are incomplete!")
        sys.exit(1)
    else:
        print("\n✓ All translations are complete!")
        sys.exit(0)

if __name__ == "__main__":
    main()
