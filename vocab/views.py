from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from pathlib import Path
import json

_WORDS_CACHE = None
_WORDS_MTIME = None


def _load_words():
    """Load words.json, refreshing automatically when the file changes."""
    global _WORDS_CACHE, _WORDS_MTIME
    path = Path(settings.BASE_DIR) / "vocab" / "data" / "words.json"
    mtime = path.stat().st_mtime
    if _WORDS_CACHE is None or _WORDS_MTIME != mtime:
        with path.open(encoding="utf-8") as f:
            _WORDS_CACHE = json.load(f)
        _WORDS_MTIME = mtime
    return _WORDS_CACHE


def home(request):
    data = _load_words()
    return render(
        request,
        "vocab/home.html",
        {
            "word_count": data["meta"]["count"],
        },
    )


def words_json(request):
    """Serve the full vocabulary dataset for client-side gameplay."""
    data = _load_words()
    response = JsonResponse(data, json_dumps_params={"ensure_ascii": False})
    response["Cache-Control"] = "no-store"
    return response
