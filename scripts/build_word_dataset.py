#!/usr/bin/env python3
"""Build a top-10k English ↔ Polish vocabulary dataset with semantic buckets."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from wordfreq import top_n_list

NS = {"tei": "http://www.tei-c.org/ns/1.0"}
LETTERS_DIR = Path("/tmp/enpl-tei/eng-pol/letters")
OUT_PATH = Path(__file__).resolve().parent.parent / "vocab" / "data" / "words.json"

# Hidden semantic buckets used only for related distractors (not shown in UI).
BUCKET_SEEDS: dict[str, list[str]] = {
    "technology": [
        "computer", "laptop", "keyboard", "mouse", "screen", "phone", "tablet",
        "internet", "website", "email", "password", "software", "hardware",
        "app", "data", "file", "download", "upload", "wifi", "battery", "charger",
        "camera", "video", "audio", "speaker", "headphones", "printer", "server",
        "network", "code", "program", "digital", "online", "offline", "cloud",
        "robot", "device", "monitor", "chip", "cable", "bluetooth", "usb",
    ],
    "food": [
        "food", "meal", "breakfast", "lunch", "dinner", "bread", "butter", "cheese",
        "milk", "egg", "meat", "chicken", "beef", "fish", "rice", "pasta", "soup",
        "salad", "fruit", "apple", "banana", "orange", "vegetable", "potato",
        "tomato", "onion", "sugar", "salt", "pepper", "coffee", "tea", "water",
        "juice", "wine", "beer", "cake", "cookie", "chocolate", "pizza", "burger",
        "sandwich", "kitchen", "cook", "bake", "fry", "boil", "taste", "hungry",
        "thirsty", "restaurant", "menu", "recipe", "ingredient", "snack", "dessert",
    ],
    "emotions": [
        "happy", "sad", "angry", "afraid", "scared", "worried", "excited", "proud",
        "ashamed", "jealous", "lonely", "bored", "tired", "surprised", "confused",
        "calm", "nervous", "love", "hate", "hope", "fear", "joy", "pain", "feel",
        "feeling", "emotion", "mood", "smile", "laugh", "cry", "tear", "stress",
        "relax", "peace", "anxiety", "confidence", "embarrassment", "guilt",
    ],
    "school": [
        "school", "student", "teacher", "class", "classroom", "lesson", "homework",
        "exam", "test", "grade", "book", "notebook", "pen", "pencil", "eraser",
        "university", "college", "study", "learn", "read", "write", "math",
        "science", "history", "language", "library", "subject", "course",
        "lecture", "degree", "diploma", "education", "knowledge", "question",
        "answer", "dictionary", "essay", "project", "research", "professor",
    ],
    "business": [
        "business", "company", "office", "work", "job", "career", "boss", "manager",
        "employee", "meeting", "salary", "money", "pay", "price", "cost", "profit",
        "loss", "market", "customer", "client", "product", "service", "sale",
        "buy", "sell", "contract", "deal", "bank", "account", "budget", "tax",
        "invoice", "investment", "stock", "trade", "industry", "economy",
        "finance", "marketing", "advertising", "brand", "team", "project",
    ],
    "home": [
        "home", "house", "apartment", "room", "kitchen", "bedroom", "bathroom",
        "living", "door", "window", "wall", "floor", "ceiling", "roof", "garden",
        "furniture", "table", "chair", "sofa", "bed", "lamp", "mirror", "closet",
        "shelf", "carpet", "curtain", "key", "lock", "clean", "dirty", "wash",
        "laundry", "dishwasher", "fridge", "oven", "microwave", "vacuum",
        "neighbor", "family", "guest", "address", "basement", "garage",
    ],
    "body": [
        "body", "head", "face", "eye", "ear", "nose", "mouth", "tooth", "tongue",
        "hair", "neck", "shoulder", "arm", "hand", "finger", "leg", "foot", "toe",
        "knee", "back", "chest", "stomach", "heart", "blood", "bone", "skin",
        "brain", "muscle", "health", "sick", "ill", "doctor", "hospital",
        "medicine", "pain", "injury", "fever", "cough", "breathe", "sleep",
    ],
    "travel": [
        "travel", "trip", "journey", "holiday", "vacation", "ticket", "passport",
        "airport", "plane", "flight", "train", "bus", "car", "taxi", "hotel",
        "map", "luggage", "suitcase", "backpack", "road", "street", "city",
        "country", "border", "customs", "tourist", "guide", "destination",
        "departure", "arrival", "delay", "station", "platform", "ferry", "ship",
        "bridge", "tunnel", "highway", "traffic", "parking", "driver",
    ],
    "nature": [
        "nature", "tree", "forest", "flower", "grass", "leaf", "plant", "river",
        "lake", "sea", "ocean", "beach", "mountain", "hill", "valley", "sky",
        "cloud", "sun", "moon", "star", "rain", "snow", "wind", "storm",
        "weather", "temperature", "hot", "cold", "warm", "cool", "earth",
        "ground", "soil", "rock", "stone", "fire", "water", "air", "environment",
    ],
    "animals": [
        "animal", "dog", "cat", "bird", "fish", "horse", "cow", "pig", "sheep",
        "chicken", "duck", "rabbit", "mouse", "rat", "lion", "tiger", "bear",
        "wolf", "fox", "deer", "elephant", "monkey", "snake", "insect", "bee",
        "butterfly", "spider", "pet", "zoo", "wild", "farm", "tail", "wing",
        "feather", "fur", "paw", "claw", "nest", "egg",
    ],
    "clothing": [
        "clothes", "shirt", "tshirt", "pants", "trousers", "jeans", "dress",
        "skirt", "jacket", "coat", "sweater", "hoodie", "socks", "shoes",
        "boots", "sneakers", "hat", "cap", "scarf", "gloves", "belt", "tie",
        "suit", "underwear", "pajamas", "pocket", "button", "zipper", "fashion",
        "wear", "outfit", "uniform", "costume", "bag", "purse", "wallet",
    ],
    "sports": [
        "sport", "game", "play", "team", "player", "coach", "match", "score",
        "win", "lose", "draw", "ball", "football", "soccer", "basketball",
        "tennis", "golf", "swimming", "running", "cycling", "gym", "exercise",
        "fitness", "training", "athlete", "championship", "medal", "goal",
        "race", "competition", "stadium", "olympic", "hockey", "volleyball",
    ],
    "time": [
        "time", "hour", "minute", "second", "day", "night", "morning", "afternoon",
        "evening", "week", "month", "year", "today", "tomorrow", "yesterday",
        "calendar", "clock", "watch", "schedule", "early", "late", "soon",
        "always", "never", "sometimes", "often", "rarely", "past", "present",
        "future", "moment", "period", "season", "spring", "summer", "autumn",
        "winter", "birthday", "deadline", "delay",
    ],
    "colors": [
        "color", "colour", "red", "blue", "green", "yellow", "orange", "purple",
        "pink", "brown", "black", "white", "gray", "grey", "gold", "silver",
        "dark", "light", "bright", "pale", "shade", "tone", "paint",
    ],
    "numbers": [
        "number", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "hundred", "thousand", "million", "billion", "first",
        "second", "third", "half", "pair", "dozen", "count", "total", "amount",
        "percent", "average", "sum", "zero", "none", "few", "many", "several",
    ],
    "family": [
        "family", "mother", "father", "parent", "mom", "dad", "son", "daughter",
        "brother", "sister", "sibling", "uncle", "aunt", "cousin", "grandmother",
        "grandfather", "grandma", "grandpa", "husband", "wife", "partner",
        "child", "baby", "kid", "relative", "wedding", "marriage", "divorce",
        "friend", "neighbor", "guest", "host",
    ],
    "city_life": [
        "city", "town", "village", "street", "road", "building", "shop", "store",
        "mall", "market", "park", "square", "bridge", "traffic", "crowd",
        "people", "police", "fire", "ambulance", "hospital", "museum", "theater",
        "cinema", "cafe", "restaurant", "bar", "club", "library", "church",
        "mosque", "temple", "station", "subway", "metro", "bus", "taxi",
    ],
    "work_tools": [
        "tool", "hammer", "nail", "screw", "screwdriver", "wrench", "drill",
        "saw", "knife", "scissors", "tape", "glue", "paint", "brush", "ladder",
        "rope", "wire", "machine", "engine", "motor", "wheel", "gear", "metal",
        "wood", "plastic", "glass", "paper", "box", "bag", "container",
    ],
    "communication": [
        "talk", "speak", "say", "tell", "ask", "answer", "listen", "hear",
        "call", "message", "letter", "mail", "email", "chat", "conversation",
        "discussion", "meeting", "phone", "news", "report", "story", "language",
        "word", "sentence", "voice", "sound", "noise", "silence", "whisper",
        "shout", "scream", "explain", "describe", "translate", "meaning",
    ],
    "actions": [
        "go", "come", "walk", "run", "jump", "sit", "stand", "lie", "sleep",
        "wake", "eat", "drink", "open", "close", "start", "stop", "begin",
        "end", "make", "do", "take", "give", "get", "put", "bring", "send",
        "find", "lose", "keep", "hold", "carry", "push", "pull", "throw",
        "catch", "break", "fix", "build", "create", "destroy", "change",
        "move", "stay", "leave", "enter", "exit", "return", "continue",
    ],
    "descriptors": [
        "big", "small", "large", "tiny", "long", "short", "tall", "high", "low",
        "wide", "narrow", "thick", "thin", "heavy", "light", "fast", "slow",
        "quick", "strong", "weak", "hard", "soft", "easy", "difficult", "simple",
        "complex", "new", "old", "young", "good", "bad", "better", "worse",
        "best", "worst", "beautiful", "ugly", "clean", "dirty", "full", "empty",
        "rich", "poor", "cheap", "expensive", "safe", "dangerous", "important",
    ],
    "places": [
        "place", "location", "area", "region", "space", "room", "world", "earth",
        "country", "nation", "state", "capital", "island", "continent", "north",
        "south", "east", "west", "left", "right", "center", "middle", "side",
        "front", "back", "top", "bottom", "inside", "outside", "near", "far",
        "here", "there", "everywhere", "nowhere", "somewhere",
    ],
}


def parse_freedict() -> dict[str, str]:
    """Parse FreeDict TEI letters into en -> first Polish gloss."""
    mapping: dict[str, str] = {}
    for path in sorted(LETTERS_DIR.glob("*.xml")):
        tree = ET.parse(path)
        root = tree.getroot()
        for entry in root.findall(".//tei:entry", NS):
            orth = entry.find("./tei:form/tei:orth", NS)
            if orth is None or not orth.text:
                continue
            en = orth.text.strip().lower()
            if not en or not re.fullmatch(r"[a-z][a-z'-]*", en):
                continue
            quotes = [
                q.text.strip()
                for q in entry.findall(".//tei:cit[@type='trans']/tei:quote", NS)
                if q.text and q.text.strip()
            ]
            if not quotes:
                continue
            pl = clean_polish(quotes[0])
            if pl and en not in mapping:
                mapping[en] = pl
    return mapping


def clean_polish(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    # Take first alternative if slash-separated
    text = text.split("/")[0].strip()
    text = text.split(";")[0].strip()
    text = text.split(",")[0].strip()
    # Drop parenthetical notes
    text = re.sub(r"\([^)]*\)", "", text).strip()
    text = text.strip(" .;,-")
    return text


def clean_google_pl(text: str) -> str:
    text = clean_polish(text)
    # Prefer shorter lemma-like forms; strip trailing inflection markers if multiword noise
    return text


MANUAL_OVERRIDES: dict[str, str] = {
    "the": "ten/ta/to",
    "a": "jakiś",
    "an": "jakiś",
    "to": "do",
    "and": "i",
    "of": "z",
    "in": "w",
    "is": "jest",
    "for": "dla",
    "that": "że",
    "you": "ty",
    "it": "to",
    "on": "na",
    "with": "z",
    "this": "to",
    "was": "był",
    "be": "być",
    "as": "jako",
    "are": "są",
    "have": "mieć",
    "or": "lub",
    "at": "przy",
    "from": "od",
    "by": "przez",
    "not": "nie",
    "your": "twój",
    "all": "wszystko",
    "can": "móc",
    "will": "będzie",
    "just": "właśnie",
    "but": "ale",
    "what": "co",
    "when": "kiedy",
    "who": "kto",
    "which": "który",
    "their": "ich",
    "there": "tam",
    "here": "tutaj",
    "they": "oni",
    "we": "my",
    "he": "on",
    "she": "ona",
    "his": "jego",
    "her": "jej",
    "my": "mój",
    "me": "mnie",
    "him": "jego",
    "us": "nas",
    "them": "ich",
    "our": "nasz",
    "if": "jeśli",
    "so": "więc",
    "than": "niż",
    "then": "potem",
    "also": "także",
    "more": "więcej",
    "most": "najbardziej",
    "some": "trochę",
    "any": "jakikolwiek",
    "no": "nie",
    "yes": "tak",
    "do": "robić",
    "does": "robi",
    "did": "zrobił",
    "done": "zrobione",
    "has": "ma",
    "had": "miał",
    "would": "by",
    "could": "mógłby",
    "should": "powinien",
    "may": "może",
    "might": "mógłby",
    "must": "musić",
    "about": "o",
    "into": "do",
    "over": "nad",
    "after": "po",
    "before": "przed",
    "between": "między",
    "under": "pod",
    "again": "znowu",
    "because": "ponieważ",
    "through": "przez",
    "during": "podczas",
    "without": "bez",
    "against": "przeciw",
    "among": "wśród",
    "across": "przez",
    "laptop": "laptop",
    "keyboard": "klawiatura",
    "mouse": "mysz",
    "speakers": "głośniki",
    "phone": "telefon",
    "computer": "komputer",
}


def build_bucket_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for bucket, words in BUCKET_SEEDS.items():
        for w in words:
            index.setdefault(w.lower(), bucket)
    return index


def assign_bucket(word: str, bucket_index: dict[str, str], rank: int) -> str:
    if word in bucket_index:
        return bucket_index[word]
    # Simple morphology: strip common endings and retry
    for suffix in ("ing", "ed", "es", "s", "ly", "tion", "ment", "ness"):
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            stem = word[: -len(suffix)]
            if stem in bucket_index:
                return bucket_index[stem]
            if stem + "e" in bucket_index:
                return bucket_index[stem + "e"]
    # Frequency bands keep distractors at similar commonness
    band = rank // 250
    return f"freq_{band:02d}"


def morph_lookup(word: str, mapping: dict[str, str]) -> str | None:
    if word in mapping:
        return mapping[word]
    if word.endswith("ies") and len(word) > 4:
        cand = word[:-3] + "y"
        if cand in mapping:
            return mapping[cand]
    for suffix in ("ing", "ed", "es", "s", "ly", "tion", "ment", "ness", "er", "est", "ers"):
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            stem = word[: -len(suffix)]
            for cand in (stem, stem + "e"):
                if cand in mapping:
                    return mapping[cand]
            if stem.endswith("i"):
                cand = stem[:-1] + "y"
                if cand in mapping:
                    return mapping[cand]
    return None


def translate_missing(words: list[str], known: dict[str, str]) -> dict[str, str]:
    missing = [w for w in words if w not in known]
    if not missing:
        return {}

    import argostranslate.translate

    filled: dict[str, str] = {}
    print(f"Translating {len(missing)} missing words via Argos (offline)...")
    for i, en in enumerate(missing, start=1):
        try:
            pl = argostranslate.translate.translate(en, "en", "pl")
            if pl:
                filled[en] = clean_google_pl(pl)
        except Exception as exc:  # noqa: BLE001
            print(f"  failed: {en}: {exc}")
        if i % 200 == 0 or i == len(missing):
            print(f"  {i}/{len(missing)}", flush=True)
    return filled


def select_english_words(n: int = 10000) -> list[str]:
    raw = top_n_list("en", n * 2)
    words: list[str] = []
    seen: set[str] = set()
    for w in raw:
        w = w.lower()
        if not re.fullmatch(r"[a-z]+", w):
            continue
        if len(w) < 2 and w not in {"a", "i"}:
            continue
        if w in seen:
            continue
        seen.add(w)
        words.append(w)
        if len(words) >= n:
            break
    if len(words) < n:
        raise SystemExit(f"Only collected {len(words)} words, need {n}")
    return words


def main() -> None:
    print("Selecting top English words...")
    english = select_english_words(10000)
    print(f"  {len(english)} words")

    print("Parsing FreeDict EN→PL...")
    freedict = parse_freedict()
    print(f"  {len(freedict)} dictionary entries")

    english_set = set(english)
    translations: dict[str, str] = {}
    translations.update({k: clean_polish(v) for k, v in freedict.items() if k in english_set})
    translations.update({k: v for k, v in MANUAL_OVERRIDES.items() if k in english_set})

    # Morphology fallback from FreeDict before machine translation
    for w in english:
        if w not in translations:
            hit = morph_lookup(w, freedict)
            if hit:
                translations[w] = clean_polish(hit)

    print(f"  coverage before MT: {len(translations)}/{len(english)}", flush=True)
    mt = translate_missing(english, translations)
    translations.update(mt)

    still_missing = [w for w in english if w not in translations or not translations[w]]
    if still_missing:
        print(f"WARNING: {len(still_missing)} words still missing translations")
        for w in still_missing:
            translations[w] = w  # last-resort identity; better than dropping

    bucket_index = build_bucket_index()
    records = []
    for rank, en in enumerate(english):
        pl = translations[en]
        bucket = assign_bucket(en, bucket_index, rank)
        records.append(
            {
                "id": rank + 1,
                "en": en,
                "pl": pl,
                "rank": rank + 1,
                "bucket": bucket,
            }
        )

    # Ensure every bucket used for play has at least 8 members by merging tiny ones
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_bucket[rec["bucket"]].append(rec)

    overflow: list[dict] = []
    for bucket, items in list(by_bucket.items()):
        if len(items) < 8:
            overflow.extend(items)
            del by_bucket[bucket]

    # Redistribute overflow into nearest freq buckets / general
    general_idx = 0
    for rec in overflow:
        placed = False
        for candidate in sorted(by_bucket.keys()):
            if candidate.startswith("freq_") and len(by_bucket[candidate]) < 80:
                rec["bucket"] = candidate
                by_bucket[candidate].append(rec)
                placed = True
                break
        if not placed:
            name = f"general_{general_idx:02d}"
            if name not in by_bucket:
                by_bucket[name] = []
            if len(by_bucket[name]) >= 40:
                general_idx += 1
                name = f"general_{general_idx:02d}"
                by_bucket[name] = []
            rec["bucket"] = name
            by_bucket[name].append(rec)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "count": len(records),
            "source_frequency": "wordfreq top English",
            "source_translations": "FreeDict eng-pol + Argos Translate fallback",
            "languages": ["en", "pl"],
        },
        "words": records,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(records)} words -> {OUT_PATH}")
    print(f"Buckets: {len(by_bucket)} (min size {min(len(v) for v in by_bucket.values())})")


if __name__ == "__main__":
    main()
