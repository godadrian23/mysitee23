#!/usr/bin/env python3
"""Re-translate plurals/known forms in vocab/data/words.json (Argos-first)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_word_dataset import (
    MANUAL_FORMS,
    clean_polish,
    english_singular,
    is_probable_english_plural,
    is_useless_identity,
    normalize_ascii_fold,
    polish_plural_from_singular,
    translate_argos,
)

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "vocab" / "data" / "words.json"

# Extra junk / non-vocab to drop if present
DROP = {
    "boobs", "bitches", "matthews", "seahawks", "sims", "oops", "olds",
    "outs", "offs", "commons", "corps",  # corps is real but ambiguous
}


def fix_plural(en: str, current_pl: str, by_en: dict[str, dict]) -> str:
    if en in MANUAL_FORMS:
        return MANUAL_FORMS[en]

    singular = english_singular(en)
    sing_pl = None
    if singular and singular in by_en:
        sing_pl = clean_polish(by_en[singular]["pl"].split("/")[0])
    elif singular and singular in MANUAL_FORMS:
        sing_pl = clean_polish(MANUAL_FORMS[singular].split("/")[0])

    arg = translate_argos(en)
    if arg and not is_useless_identity(en, arg):
        arg_base = clean_polish(arg)
        if not sing_pl or normalize_ascii_fold(arg_base) != normalize_ascii_fold(sing_pl):
            if not (sing_pl and arg_base == sing_pl + "e"):
                return arg_base

    if sing_pl:
        plural = polish_plural_from_singular(sing_pl)
        if plural and plural != sing_pl:
            return plural

    return current_pl


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    words = [w for w in data["words"] if w["en"] not in DROP]
    by_en = {w["en"]: w for w in words}

    # Apply manual singular/plural forms first
    changed = 0
    for en, pl in MANUAL_FORMS.items():
        if en in by_en and by_en[en]["pl"] != pl:
            by_en[en]["pl"] = pl
            changed += 1

    plurals = [w for w in words if is_probable_english_plural(w["en"])]
    print(f"Re-translating {len(plurals)} plural candidates...", flush=True)
    for i, w in enumerate(plurals, start=1):
        new_pl = fix_plural(w["en"], w["pl"], by_en)
        if new_pl != w["pl"]:
            w["pl"] = new_pl
            changed += 1
        if i % 200 == 0 or i == len(plurals):
            print(f"  {i}/{len(plurals)} (changed {changed})", flush=True)

    # Re-id if we dropped rows
    for idx, w in enumerate(words, start=1):
        w["id"] = idx
        w["rank"] = idx

    data["words"] = words
    data["meta"]["count"] = len(words)
    data["meta"]["plural_fix"] = "argos-first + manual forms"
    PATH.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(words)} words; {changed} translations updated", flush=True)

    for probe in (
        "sector", "sectors", "doctor", "doctors", "actor", "actors",
        "factor", "factors", "error", "errors", "user", "users",
        "member", "members", "player", "players",
    ):
        hit = next((w for w in words if w["en"] == probe), None)
        print(f"  {probe}: {hit['pl'] if hit else None}", flush=True)


if __name__ == "__main__":
    main()
