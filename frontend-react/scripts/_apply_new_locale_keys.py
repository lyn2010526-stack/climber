#!/usr/bin/env python3
"""One-shot helper: merge the namespaces added by the i18n convergence pass."""

import json
from collections import OrderedDict
from pathlib import Path

LOCALES = Path(__file__).resolve().parents[1] / "src" / "locales"

PAYLOAD = json.loads(Path(__file__).with_name("new_locale_keys.json").read_text(encoding="utf-8"))


def bundle_for(lang):
    if lang == "en":
        return PAYLOAD["all"]
    return PAYLOAD[lang]


def deep_merge(target, incoming):
    added = 0
    for key, value in incoming.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            added += deep_merge(target[key], value)
        else:
            if key not in target:
                added += 1
            target[key] = value
    return added


for path in sorted(LOCALES.glob("*.json")):
    lang = path.stem
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)
    before = json.dumps(data, ensure_ascii=False, sort_keys=True)
    added = deep_merge(data, bundle_for(lang))
    data = json.loads(json.dumps(data), object_pairs_hook=OrderedDict)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{lang}: added {added} new keys, {len(data)} top-level namespaces, changed={json.dumps(data, ensure_ascii=False, sort_keys=True) != before}")
