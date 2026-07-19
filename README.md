"""
Vocab Snap Trainer (Rapid Mode)
================================

A fast-paced English ↔ Polish vocabulary trainer.

Play
----
1. Create/activate a virtualenv and install deps::

     python3 -m venv my-venv
     source my-venv/bin/activate
     pip install -r requirements.txt

2. Run the server::

     python manage.py runserver

3. Open http://127.0.0.1:8000/ on your phone (same Wi‑Fi) or laptop.

Gameplay
--------
- Prompt word centered at the top (randomly English or Polish)
- 8 related multiple-choice answers
- Hard 1-second timer — miss if you don't tap in time
- Modes: Endless (chase high streak/score) and Fixed rounds (presets or any N)
- Progress stored in browser localStorage (guest-friendly for iPhone)

Dataset
-------
``vocab/data/words.json`` — top 10,000 everyday English words with Polish
translations and hidden semantic buckets for related distractors.

Rebuild with::

    python scripts/build_word_dataset.py

(Requires FreeDict TEI files under ``/tmp/enpl-tei`` and Argos EN→PL model.)
"""
