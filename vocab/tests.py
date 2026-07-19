from django.test import Client, TestCase
from django.urls import reverse
import json
from pathlib import Path

class VocabSnapTests(TestCase):
    def setUp(self):
        self.client = Client()

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
        path = Path(__file__).resolve().parent / "data" / "words.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        counts = {}
        for word in data["words"]:
            counts[word["bucket"]] = counts.get(word["bucket"], 0) + 1
        self.assertTrue(counts)
        self.assertGreaterEqual(min(counts.values()), 8)
