from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from pathlib import Path
import json

_WORDS_CACHE = None


def _load_words():
    global _WORDS_CACHE
    if _WORDS_CACHE is None:
        path = Path(settings.BASE_DIR) / "vocab" / "data" / "words.json"
        with path.open(encoding="utf-8") as f:
            _WORDS_CACHE = json.load(f)
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
    return JsonResponse(data, json_dumps_params={"ensure_ascii": False})
