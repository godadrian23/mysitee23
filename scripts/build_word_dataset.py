#!/usr/bin/env python3
"""Build a clean top-10k English ↔ Polish vocabulary dataset.

Quality rules:
- Drop person names (Thomas, John, …) and junk tokens (http, lol, …)
- Prefer dictionary glosses; fall back to Argos for the exact surface form
- Keep English/Polish number agreement (duck↔kaczka, ducks↔kaczki)
- Reject useless identity pairs unless the word is a known loanword
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from wordfreq import top_n_list

try:
    from nltk.corpus import names as nltk_names
except ImportError:  # pragma: no cover
    nltk_names = None

NS = {"tei": "http://www.tei-c.org/ns/1.0"}
LETTERS_DIR = Path("/tmp/enpl-tei/eng-pol/letters")
OUT_PATH = Path(__file__).resolve().parent.parent / "vocab" / "data" / "words.json"

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
        "door", "window", "wall", "floor", "ceiling", "roof", "garden",
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
        "clothes", "shirt", "pants", "trousers", "jeans", "dress", "skirt",
        "jacket", "coat", "sweater", "hoodie", "socks", "shoes", "boots",
        "sneakers", "hat", "cap", "scarf", "gloves", "belt", "tie", "suit",
        "underwear", "pajamas", "pocket", "button", "zipper", "fashion",
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
        "people", "police", "ambulance", "hospital", "museum", "theater",
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

NAME_ALLOWLIST = {
    "may", "will", "june", "july", "august", "mark", "art", "grace", "hope",
    "joy", "bill", "bob", "jack", "robin", "chase", "grant", "clay", "stone",
    "page", "lake", "forest", "summer", "winter", "spring", "autumn", "fall",
    "dawn", "holly", "ivy", "rose", "violet", "olive", "ginger", "cherry",
    "amber", "crystal", "jade", "pearl", "ruby", "coral", "heath", "brook",
    "cliff", "dale", "glen", "vale", "reed", "ash", "bay", "dean", "earl",
    "king", "queen", "prince", "duke", "baron", "major", "general", "doctor",
    "nurse", "teacher", "student", "mother", "father", "brother", "sister",
    "cousin", "uncle", "aunt", "son", "daughter", "baby", "child", "man",
    "woman", "boy", "girl", "people", "person", "human", "young", "green",
    "cook", "long", "wood", "bell", "hill", "brown", "white", "black", "gray",
    "grey", "blue", "gold", "silver", "frank", "pat", "chris", "jordan", "taylor",
    "morgan", "casey", "kelly", "bailey", "harper", "carter", "parker", "hunter",
}

BLOCKLIST = {
    "http", "https", "www", "html", "com", "org", "net", "edu", "gov",
    "lol", "omg", "btw", "imo", "idk", "tbh", "smh", "nvm", "fyi", "asap",
    "wanna", "gonna", "gotta", "kinda", "sorta", "dunno", "lemme", "gimme",
    "u", "ur", "r", "ya", "yall", "ain", "dont", "didnt", "cant", "wont",
    "isnt", "wasnt", "arent", "havent", "hasnt", "wouldnt", "couldnt",
    "shouldnt", "im", "ive", "youre", "theyre", "hes", "shes", "thats",
    "whats", "wheres", "theres", "heres", "lets", "whos",
    "ii", "iii", "iv", "vi", "vii", "viii", "ix", "xi", "xii", "xx", "xxx",
    "mr", "mrs", "ms", "dr", "jr", "sr", "st", "rd", "ave",
    "vs", "etc", "eg", "ie", "nb", "ps", "fwd",
    "de", "la", "el", "le", "des", "del", "van", "von", "da", "di", "du",
    "san", "santa", "los", "las", "rio", "porto",
    "facebook", "google", "youtube", "twitter", "instagram", "tiktok",
    "amazon", "netflix", "spotify", "iphone", "android",
    "jesus", "christ", "allah", "bible", "quran",
}

LOANWORDS_OK = {
    "system", "video", "problem", "plan", "program", "film", "bank", "park",
    "model", "internet", "hotel", "radio", "taxi", "bus", "sport", "golf",
    "tennis", "album", "status", "partner", "metal", "marketing", "manager",
    "business", "student", "region", "weekend", "bar", "plus", "menu", "salad",
    "pizza", "burger", "jeans", "blog", "media", "forum", "test", "start",
    "stop", "normal", "ideal", "total", "final", "original", "personal",
    "social", "global", "digital", "manual", "automatic", "public", "private",
    "legal", "formal", "standard", "premium", "online", "laptop", "tablet",
    "robot", "wifi", "email", "app", "club", "pub", "cent", "dollar", "euro",
    "hobby", "picnic", "camping", "parking", "meeting", "briefing", "set",
    "box", "top", "ok", "okay",
}

MANUAL: dict[str, str] = {
    "the": "ten / ta / to",
    "a": "jakiś",
    "an": "jakiś",
    "to": "do",
    "and": "i",
    "of": "z",
    "in": "w",
    "is": "jest",
    "for": "dla",
    "that": "że / tamten",
    "you": "ty / wy",
    "it": "to / ono",
    "on": "na",
    "with": "z",
    "this": "to / ten",
    "was": "był",
    "be": "być",
    "as": "jako / jak",
    "are": "są",
    "have": "mieć",
    "or": "lub / albo",
    "at": "przy / u",
    "from": "od / z",
    "by": "przez / koło",
    "not": "nie",
    "your": "twój / wasz",
    "all": "wszystko / wszyscy",
    "can": "móc / potrafić",
    "will": "będzie / wola",
    "just": "właśnie / tylko",
    "but": "ale",
    "what": "co",
    "when": "kiedy",
    "who": "kto",
    "which": "który",
    "their": "ich",
    "there": "tam",
    "here": "tutaj",
    "they": "oni / one",
    "we": "my",
    "he": "on",
    "she": "ona",
    "his": "jego",
    "her": "jej",
    "my": "mój",
    "me": "mnie / mi",
    "him": "jego / niego",
    "us": "nas / nam",
    "them": "ich / nich",
    "our": "nasz",
    "if": "jeśli",
    "so": "więc / tak",
    "than": "niż",
    "then": "potem / wtedy",
    "also": "także",
    "more": "więcej",
    "most": "najbardziej / większość",
    "some": "kilka / trochę",
    "any": "jakikolwiek / żaden",
    "no": "nie / żaden",
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
    "may": "może / maj",
    "might": "mógłby",
    "must": "musić",
    "about": "o / około",
    "into": "do",
    "over": "nad / przez",
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
    "across": "przez / w poprzek",
    "up": "w górę",
    "out": "na zewnątrz",
    "how": "jak",
    "where": "gdzie",
    "why": "dlaczego",
    "now": "teraz",
    "only": "tylko",
    "very": "bardzo",
    "even": "nawet",
    "back": "plecy / z powrotem",
    "good": "dobry",
    "new": "nowy",
    "first": "pierwszy",
    "last": "ostatni",
    "long": "długi",
    "great": "świetny / wielki",
    "little": "mały / trochę",
    "own": "własny",
    "other": "inny",
    "old": "stary",
    "right": "prawy / prawo / racja",
    "big": "duży",
    "high": "wysoki",
    "different": "inny / różny",
    "small": "mały",
    "large": "duży",
    "next": "następny",
    "early": "wczesny / wcześnie",
    "young": "młody",
    "important": "ważny",
    "few": "kilka",
    "public": "publiczny",
    "bad": "zły",
    "same": "ten sam",
    "able": "zdolny",
    "duck": "kaczka",
    "ducks": "kaczki",
    "dog": "pies",
    "dogs": "psy",
    "cat": "kot",
    "cats": "koty",
    "book": "książka",
    "books": "książki",
    "child": "dziecko",
    "children": "dzieci",
    "man": "mężczyzna",
    "men": "mężczyźni",
    "woman": "kobieta",
    "women": "kobiety",
    "mouse": "mysz",
    "mice": "myszy",
    "foot": "stopa",
    "feet": "stopy",
    "tooth": "ząb",
    "teeth": "zęby",
    "person": "osoba",
    "people": "ludzie",
    "leaf": "liść",
    "leaves": "liście",
    "life": "życie",
    "lives": "życia / żyje",
    "knife": "nóż",
    "knives": "noże",
    "wife": "żona",
    "wives": "żony",
    "take": "brać / wziąć",
    "takes": "bierze",
    "took": "wziął",
    "taken": "wzięty",
    "put": "kłaść / położyć",
    "puts": "kładzie",
    "am": "jestem",
    "get": "dostać / brać",
    "gets": "dostaje",
    "got": "dostał",
    "make": "robić / tworzyć",
    "makes": "robi",
    "made": "zrobiony",
    "go": "iść / jechać",
    "goes": "idzie",
    "went": "poszedł",
    "gone": "poszedł",
    "come": "przychodzić",
    "comes": "przychodzi",
    "came": "przyszedł",
    "see": "widzieć",
    "sees": "widzi",
    "saw": "piła / widział",
    "seen": "widziany",
    "know": "wiedzieć / znać",
    "knows": "wie",
    "knew": "wiedział",
    "known": "znany",
    "think": "myśleć",
    "thinks": "myśli",
    "thought": "myśl / myślał",
    "say": "mówić / powiedzieć",
    "says": "mówi",
    "said": "powiedział",
    "tell": "mówić / opowiadać",
    "tells": "mówi",
    "told": "powiedział",
    "give": "dawać / dać",
    "gives": "daje",
    "gave": "dał",
    "given": "dany",
    "find": "znaleźć",
    "finds": "znajduje",
    "found": "znaleziony",
    "use": "używać",
    "uses": "używa",
    "used": "używany",
    "want": "chcieć",
    "wants": "chce",
    "wanted": "chciał",
    "need": "potrzebować",
    "needs": "potrzebuje",
    "needed": "potrzebny",
    "create": "tworzyć",
    "creates": "tworzy",
    "created": "stworzony",
    "post": "poczta / wpis",
    "bit": "odrobina / bit",
    "fine": "w porządku / grzywna",
    "rock": "skała / rock",
    "spot": "miejsce / plama",
    "house": "dom",
    "home": "dom",
    "love": "miłość / kochać",
    "ok": "w porządku",
    "okay": "w porządku",
}

IRREGULAR_SINGULAR = {
    "children": "child",
    "men": "man",
    "women": "woman",
    "people": "person",
    "mice": "mouse",
    "feet": "foot",
    "teeth": "tooth",
    "geese": "goose",
    "leaves": "leaf",
    "knives": "knife",
    "wives": "wife",
    "lives": "life",
    "selves": "self",
    "thieves": "thief",
}


def clean_polish(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    text = text.split(";")[0].strip()
    if " / " in text:
        text = text.split(" / ")[0].strip()
    elif "/" in text and " " not in text.split("/")[0]:
        text = text.split("/")[0].strip()
    text = text.split(",")[0].strip()
    text = re.sub(r"\([^)]*\)", "", text).strip()
    return text.strip(" .;,-–—")


def parse_freedict() -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not LETTERS_DIR.exists():
        print("WARNING: FreeDict TEI not found at", LETTERS_DIR)
        return mapping
    for path in sorted(LETTERS_DIR.glob("*.xml")):
        root = ET.parse(path).getroot()
        for entry in root.findall(".//tei:entry", NS):
            orth = entry.find("./tei:form/tei:orth", NS)
            if orth is None or not orth.text:
                continue
            en = orth.text.strip().lower()
            if not re.fullmatch(r"[a-z][a-z'-]*", en):
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


def load_person_names() -> set[str]:
    names: set[str] = set()
    if nltk_names is not None:
        for filename in ("male.txt", "female.txt"):
            try:
                names.update(n.lower() for n in nltk_names.words(filename))
            except LookupError:
                import nltk as _nltk

                _nltk.download("names", quiet=True)
                names.update(n.lower() for n in nltk_names.words(filename))
    names.update(
        {
            "thomas", "john", "paul", "mary", "michael", "george", "william",
            "robert", "richard", "joe", "david", "james", "peter", "anna",
            "sarah", "jennifer", "elizabeth", "susan", "jessica", "daniel",
            "matthew", "anthony", "donald", "steven", "andrew", "joshua",
            "kenneth", "kevin", "brian", "edward", "ronald", "timothy", "jason",
            "jeffrey", "ryan", "jacob", "gary", "nicholas", "eric", "jonathan",
            "stephen", "larry", "justin", "brandon", "benjamin", "samuel",
            "gregory", "alexander", "raymond", "patrick", "dennis", "jerry",
            "tyler", "aaron", "jose", "adam", "nathan", "henry", "douglas",
            "zachary", "kyle", "noah", "ethan", "jeremy", "walter", "keith",
            "roger", "terry", "austin", "sean", "gerald", "carl", "harold",
            "dylan", "arthur", "lawrence", "jesse", "bryan", "bruce", "gabriel",
            "logan", "albert", "willie", "alan", "ralph", "roy", "tom", "tommy",
            "tony", "mike", "bobby", "jimmy", "tim", "dan", "danny", "steve",
            "dave", "alex", "ben", "nick", "matt", "katie", "kate", "kathy",
            "nancy", "betty", "helen", "sandra", "donna", "carol", "ruth",
            "sharon", "michelle", "laura", "emily", "kimberly", "deborah",
            "stephanie", "rebecca", "virginia", "catherine", "christine", "max",
            "leo", "lucy", "lily", "sophie", "olivia", "emma", "chloe", "mia",
            "harry", "oscar", "charlie", "louis", "lucas",
        }
    )
    return names - NAME_ALLOWLIST


def is_probable_english_plural(word: str) -> bool:
    if word in IRREGULAR_SINGULAR:
        return True
    if len(word) < 4 or not word.endswith("s"):
        return False
    if word.endswith(("ss", "us", "is", "ous", "ics", "itis", "esis", "osis", "ness", "less")):
        return False
    return True


def english_singular(word: str) -> str | None:
    if word in IRREGULAR_SINGULAR:
        return IRREGULAR_SINGULAR[word]
    if not is_probable_english_plural(word):
        return None
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith(("ches", "shes", "xes", "sses", "zes")) and len(word) > 4:
        return word[:-2]
    if word.endswith("ves") and len(word) > 4:
        stem = word[:-3]
        return stem + ("fe" if stem.endswith("i") else "f")
    if word.endswith("es") and len(word) > 4 and word[-3] in "sxz":
        return word[:-2]
    if word.endswith("s"):
        return word[:-1]
    return None


def polish_plural_from_singular(singular: str) -> str | None:
    s = singular.strip().lower()
    if not s or " " in s or "/" in s:
        return None
    irregular = {
        "pies": "psy",
        "kot": "koty",
        "kaczka": "kaczki",
        "książka": "książki",
        "dziecko": "dzieci",
        "mężczyzna": "mężczyźni",
        "kobieta": "kobiety",
        "osoba": "osoby",
        "człowiek": "ludzie",
        "mysz": "myszy",
        "stopa": "stopy",
        "ząb": "zęby",
        "liść": "liście",
        "nóż": "noże",
        "żona": "żony",
        "oko": "oczy",
        "ucho": "uszy",
        "ręka": "ręce",
        "brat": "bracia",
        "przyjaciel": "przyjaciele",
        "dom": "domy",
        "samochód": "samochody",
        "ptak": "ptaki",
        "kwiat": "kwiaty",
        "stół": "stoły",
        "koń": "konie",
        "dzień": "dni",
    }
    if s in irregular:
        return irregular[s]
    if s.endswith("ka"):
        return s[:-2] + "ki"
    if s.endswith("ga"):
        return s[:-2] + "gi"
    if s.endswith("a"):
        return s[:-1] + "y"
    if s.endswith("ek"):
        return s[:-2] + "ki"
    if s.endswith("ec"):
        return s[:-2] + "ce"
    if s.endswith(("ć", "ś", "ź", "ń", "j", "l")):
        return s + "e"
    if re.search(r"[bdfghklmnprstwz]$", s) or s.endswith("ch"):
        return s + "y"
    return None


def normalize_ascii_fold(text: str) -> str:
    repl = str.maketrans(
        {
            "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o",
            "ś": "s", "ź": "z", "ż": "z",
        }
    )
    return text.translate(repl).lower()


def is_useless_identity(en: str, pl: str) -> bool:
    if not pl:
        return True
    en_n = normalize_ascii_fold(en)
    pl_n = normalize_ascii_fold(pl.split("/")[0].split()[0])
    if en_n != pl_n:
        return False
    return en.lower() not in LOANWORDS_OK


def translate_argos(en: str) -> str | None:
    import argostranslate.translate

    try:
        pl = argostranslate.translate.translate(en, "en", "pl")
    except Exception:  # noqa: BLE001
        return None
    return clean_polish(pl) if pl else None


def morph_lookup(word: str, mapping: dict[str, str]) -> str | None:
    if word in mapping:
        return mapping[word]
    if word.endswith("ies") and len(word) > 4:
        cand = word[:-3] + "y"
        if cand in mapping:
            return mapping[cand]
    for suffix in ("ing", "ed", "es", "s", "ly", "tion", "ment", "ness", "er", "est"):
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


def translate_word(en: str, freedict: dict[str, str], cache: dict[str, str]) -> str | None:
    if en in cache:
        return cache[en]
    if en in MANUAL:
        cache[en] = MANUAL[en]
        return cache[en]

    if is_probable_english_plural(en):
        singular = english_singular(en)
        if singular:
            sing_pl = translate_word(singular, freedict, cache)
            if sing_pl:
                base = clean_polish(sing_pl.split("/")[0])
                plural = polish_plural_from_singular(base)
                if plural and plural != base:
                    cache[en] = plural
                    return cache[en]
            arg = translate_argos(en)
            if arg and not is_useless_identity(en, arg):
                if singular:
                    sing_pl2 = cache.get(singular)
                    if sing_pl2 and clean_polish(arg) == clean_polish(sing_pl2.split("/")[0]):
                        forced = polish_plural_from_singular(clean_polish(sing_pl2.split("/")[0]))
                        if forced:
                            cache[en] = forced
                            return cache[en]
                cache[en] = arg
                return cache[en]

    if en in freedict:
        pl = clean_polish(freedict[en])
        if pl and not is_useless_identity(en, pl):
            cache[en] = pl
            return cache[en]

    hit = morph_lookup(en, freedict)
    if hit:
        pl = clean_polish(hit)
        if pl and not is_useless_identity(en, pl):
            if not (is_probable_english_plural(en) and polish_plural_from_singular(pl) and pl == clean_polish(hit)):
                # If this is plural and morph returned singular gloss, pluralize it
                if is_probable_english_plural(en):
                    forced = polish_plural_from_singular(pl)
                    if forced and forced != pl:
                        cache[en] = forced
                        return cache[en]
                else:
                    cache[en] = pl
                    return cache[en]

    arg = translate_argos(en)
    if arg and not is_useless_identity(en, arg):
        cache[en] = arg
        return cache[en]
    return None


def should_skip_token(en: str, person_names: set[str], freedict: dict[str, str]) -> bool:
    if en in BLOCKLIST:
        return True
    if not re.fullmatch(r"[a-z]+", en):
        return True
    if len(en) == 1 and en not in {"a", "i"}:
        return True
    # Drop person names only when they have no real dictionary sense.
    if en in person_names and en not in NAME_ALLOWLIST and en not in MANUAL and en not in freedict:
        return True
    return False


def build_bucket_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for bucket, words in BUCKET_SEEDS.items():
        for w in words:
            index.setdefault(w.lower(), bucket)
    return index


def assign_bucket(word: str, bucket_index: dict[str, str], rank: int) -> str:
    if word in bucket_index:
        return bucket_index[word]
    singular = english_singular(word)
    if singular and singular in bucket_index:
        return bucket_index[singular]
    for suffix in ("ing", "ed", "es", "s", "ly", "tion", "ment", "ness"):
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            stem = word[: -len(suffix)]
            if stem in bucket_index:
                return bucket_index[stem]
            if stem + "e" in bucket_index:
                return bucket_index[stem + "e"]
    return f"freq_{rank // 250:02d}"


def candidate_english(limit: int = 35000) -> list[str]:
    raw = top_n_list("en", limit)
    out: list[str] = []
    seen: set[str] = set()
    for w in raw:
        w = w.lower()
        if w in seen or not re.fullmatch(r"[a-z]+", w):
            continue
        seen.add(w)
        out.append(w)
    return out


def main() -> None:
    print("Loading filters & dictionaries...", flush=True)
    person_names = load_person_names()
    print(f"  person-name filter: {len(person_names)}", flush=True)
    freedict = parse_freedict()
    print(f"  FreeDict entries: {len(freedict)}", flush=True)

    # Fix known bad/odd FreeDict head glosses for everyday senses
    freedict.update(
        {
            "house": "dom",
            "home": "dom",
            "love": "miłość / kochać",
            "rock": "skała / rock",
            "bear": "niedźwiedź / znosić",
            "fan": "wentylator / kibic",
            "miss": "tęsknić / panna / chybiać",
            "lie": "kłamać / leżeć",
            "light": "światło / lekki",
            "present": "obecny / prezent",
            "letter": "list / litera",
            "match": "mecz / zapałka / pasować",
            "park": "park / parkować",
        }
    )

    bucket_index = build_bucket_index()
    cache: dict[str, str] = {}
    records: list[dict] = []
    skipped = {"name": 0, "block": 0, "bad_translation": 0, "identity": 0}

    print("Selecting & translating vocabulary...", flush=True)
    for en in candidate_english():
        if len(records) >= 10000:
            break
        if should_skip_token(en, person_names, freedict):
            if en in person_names and en not in freedict:
                skipped["name"] += 1
            else:
                skipped["block"] += 1
            continue

        pl = translate_word(en, freedict, cache)
        if not pl:
            skipped["bad_translation"] += 1
            continue
        if is_useless_identity(en, pl):
            skipped["identity"] += 1
            continue

        # Extra guard: person-name with near-identical translation
        if en in person_names and en not in NAME_ALLOWLIST and en not in MANUAL:
            if normalize_ascii_fold(pl.split("/")[0].split()[0]) == normalize_ascii_fold(en):
                skipped["name"] += 1
                continue

        if is_probable_english_plural(en):
            singular = english_singular(en)
            if singular and singular in cache:
                sing_pl = clean_polish(cache[singular].split("/")[0])
                pl_base = clean_polish(pl.split("/")[0])
                if pl_base == sing_pl:
                    forced = polish_plural_from_singular(sing_pl)
                    if forced and forced != sing_pl:
                        pl = forced
                    else:
                        skipped["bad_translation"] += 1
                        continue

        rank = len(records) + 1
        records.append(
            {
                "id": rank,
                "en": en,
                "pl": pl,
                "rank": rank,
                "bucket": assign_bucket(en, bucket_index, rank - 1),
            }
        )
        if rank % 500 == 0:
            print(f"  kept {rank}/10000 (skipped {sum(skipped.values())})", flush=True)

    if len(records) < 10000:
        raise SystemExit(f"Only collected {len(records)} clean words; need 10000")

    by_bucket: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_bucket[rec["bucket"]].append(rec)

    overflow: list[dict] = []
    for bucket, items in list(by_bucket.items()):
        if len(items) < 8:
            overflow.extend(items)
            del by_bucket[bucket]

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

    payload = {
        "meta": {
            "count": len(records),
            "source_frequency": "wordfreq top English (filtered)",
            "source_translations": "FreeDict eng-pol + Argos + manual number fixes",
            "languages": ["en", "pl"],
            "filters": [
                "person_names_without_dictionary_sense",
                "blocklist_slang_urls_brands",
                "reject_useless_identity_pairs",
                "plural_number_agreement",
            ],
        },
        "words": records,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} words -> {OUT_PATH}", flush=True)
    print(f"Skipped: {skipped}", flush=True)
    print(
        f"Buckets: {len(by_bucket)} (min size {min(len(v) for v in by_bucket.values())})",
        flush=True,
    )
    for probe in (
        "duck", "ducks", "cat", "cats", "dog", "dogs", "book", "books",
        "thomas", "john", "house", "love", "see", "happy", "take", "created",
    ):
        hit = next((r for r in records if r["en"] == probe), None)
        print(f"  {probe}: {hit}", flush=True)


if __name__ == "__main__":
    main()
