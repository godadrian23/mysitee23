import json
from pathlib import Path

from django.test import Client, TestCase
from django.urls import reverse


class VocabSnapTests(TestCase):
    def setUp(self):
        self.client = Client()
        path = Path(__file__).resolve().parent / "data" / "words.json"
        self.data = json.loads(path.read_text(encoding="utf-8"))
        self.by_en = {w["en"]: w for w in self.data["words"]}

    def test_home_renders(self):
        response = self.client.get(reverse("vocab_home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vocab Snap")
        self.assertContains(response, "Rapid Mode")
        self.assertContains(response, "Endless")
        self.assertContains(response, "Fixed rounds")

    def test_words_api_has_ten_thousand(self):
        response = self.client.get(reverse("vocab_words"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["count"], 10000)
        self.assertEqual(len(payload["words"]), 10000)
        sample = payload["words"][0]
        self.assertIn("en", sample)
        self.assertIn("pl", sample)
        self.assertIn("bucket", sample)

    def test_buckets_large_enough_for_eight_choices(self):
        counts = {}
        for word in self.data["words"]:
            counts[word["bucket"]] = counts.get(word["bucket"], 0) + 1
        self.assertTrue(counts)
        self.assertGreaterEqual(min(counts.values()), 8)

    def test_person_names_excluded(self):
        for name in ("thomas", "john", "michael", "jennifer"):
            self.assertNotIn(name, self.by_en)

    def test_plural_number_agreement(self):
        cases = {
            "duck": "kaczka",
            "ducks": "kaczki",
            "cat": "kot",
            "cats": "koty",
            "dog": "pies",
            "dogs": "psy",
            "book": "książka",
            "books": "książki",
            "sector": "sektor",
            "sectors": "sektory",
            "doctor": "lekarz",
            "doctors": "lekarze",
            "error": "błąd",
            "errors": "błędy",
            "user": "użytkownik",
            "users": "użytkownicy",
            "actor": "aktor",
            "actors": "aktorzy",
            "factor": "czynnik",
            "factors": "czynniki",
            "member": "członek",
            "members": "członkowie",
            "player": "gracz",
            "players": "gracze",
        }
        for en, pl in cases.items():
            self.assertIn(en, self.by_en)
            self.assertEqual(self.by_en[en]["pl"].split(" / ")[0], pl)
