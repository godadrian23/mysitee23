(() => {
  const SNAP_MS = 3000;
  const CHOICE_COUNT = 8;
  const FEEDBACK_MS = 650;
  const STORAGE_KEY = window.VOCAB_SNAP.storageKey;

  const els = {
    setup: document.getElementById("screen-setup"),
    play: document.getElementById("screen-play"),
    results: document.getElementById("screen-results"),
    fixedControls: document.getElementById("fixed-controls"),
    roundsInput: document.getElementById("rounds-input"),
    btnStart: document.getElementById("btn-start"),
    loadStatus: document.getElementById("load-status"),
    bestStreak: document.getElementById("best-streak"),
    bestScore: document.getElementById("best-score"),
    hudStreak: document.getElementById("hud-streak"),
    hudScore: document.getElementById("hud-score"),
    hudProgress: document.getElementById("hud-progress"),
    hudProgressWrap: document.getElementById("hud-progress-wrap"),
    btnQuit: document.getElementById("btn-quit"),
    timerBar: document.getElementById("timer-bar"),
    directionHint: document.getElementById("direction-hint"),
    promptWord: document.getElementById("prompt-word"),
    feedback: document.getElementById("feedback"),
    choices: document.getElementById("choices"),
    resultsTitle: document.getElementById("results-title"),
    resScore: document.getElementById("res-score"),
    resStreak: document.getElementById("res-streak"),
    resCorrect: document.getElementById("res-correct"),
    resMissed: document.getElementById("res-missed"),
    resNote: document.getElementById("res-note"),
    btnAgain: document.getElementById("btn-again"),
    btnHome: document.getElementById("btn-home"),
  };

  let words = [];
  let byBucket = new Map();
  let ready = false;
  let session = null;
  let roundTimer = null;
  let feedbackTimer = null;
  let locked = false;

  function loadStats() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    } catch {
      return {};
    }
  }

  function saveStats(patch) {
    const next = { ...loadStats(), ...patch };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    return next;
  }

  function refreshHighscores() {
    const stats = loadStats();
    els.bestStreak.textContent = String(stats.bestStreak || 0);
    els.bestScore.textContent = String(stats.bestEndlessScore || 0);
  }

  function show(screen) {
    [els.setup, els.play, els.results].forEach((el) => el.classList.add("is-hidden"));
    screen.classList.remove("is-hidden");
  }

  function selectedMode() {
    return document.querySelector('input[name="mode"]:checked')?.value || "endless";
  }

  function selectedRounds() {
    const n = parseInt(els.roundsInput.value, 10);
    if (!Number.isFinite(n) || n < 1) return 100;
    return Math.min(10000, n);
  }

  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function pickRelatedChoices(target) {
    const pool = (byBucket.get(target.bucket) || []).filter((w) => w.id !== target.id);
    let distractors = shuffle(pool).slice(0, CHOICE_COUNT - 1);

    if (distractors.length < CHOICE_COUNT - 1) {
      const extras = shuffle(words.filter((w) => w.id !== target.id && !distractors.includes(w)));
      distractors = distractors.concat(extras.slice(0, CHOICE_COUNT - 1 - distractors.length));
    }

    return shuffle([target, ...distractors.slice(0, CHOICE_COUNT - 1)]);
  }

  function updateHud() {
    els.hudStreak.textContent = String(session.streak);
    els.hudScore.textContent = String(session.score);
    if (session.mode === "fixed") {
      els.hudProgressWrap.style.display = "";
      els.hudProgress.textContent = `${session.roundIndex}/${session.totalRounds}`;
    } else {
      els.hudProgressWrap.style.display = "none";
    }
  }

  function clearTimers() {
    if (roundTimer) {
      clearTimeout(roundTimer);
      roundTimer = null;
    }
    if (feedbackTimer) {
      clearTimeout(feedbackTimer);
      feedbackTimer = null;
    }
  }

  function startTimerBar() {
    els.timerBar.classList.remove("running", "freeze");
    // restart animation
    void els.timerBar.offsetWidth;
    els.timerBar.style.setProperty("--snap-ms", `${SNAP_MS}ms`);
    els.timerBar.classList.add("running");
  }

  function freezeTimerBar() {
    els.timerBar.classList.add("freeze");
    els.timerBar.classList.remove("running");
  }

  function nextRound() {
    clearTimers();
    locked = false;
    els.feedback.textContent = "";
    els.feedback.className = "feedback";

    if (session.mode === "fixed" && session.roundIndex >= session.totalRounds) {
      endSession("finished");
      return;
    }

    session.roundIndex += 1;
    const target = words[Math.floor(Math.random() * words.length)];
    const toPolish = Math.random() < 0.5;
    const choices = pickRelatedChoices(target);

    session.current = { target, toPolish, choices };
    updateHud();

    els.directionHint.textContent = toPolish ? "EN → PL" : "PL → EN";
    els.promptWord.textContent = toPolish ? target.en : target.pl;
    els.promptWord.classList.remove("pulse");
    void els.promptWord.offsetWidth;
    els.promptWord.classList.add("pulse");

    els.choices.innerHTML = "";
    choices.forEach((word) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "choice-btn";
      btn.textContent = toPolish ? word.pl : word.en;
      btn.dataset.id = String(word.id);
      btn.addEventListener("click", () => onChoice(word, btn));
      els.choices.appendChild(btn);
    });

    startTimerBar();
    roundTimer = setTimeout(() => onTimeout(), SNAP_MS);
  }

  function disableChoices() {
    [...els.choices.querySelectorAll("button")].forEach((b) => {
      b.disabled = true;
    });
  }

  function revealAnswer(selectedId) {
    [...els.choices.querySelectorAll("button")].forEach((b) => {
      const id = Number(b.dataset.id);
      if (id === session.current.target.id) b.classList.add("correct");
      if (selectedId != null && id === selectedId && id !== session.current.target.id) {
        b.classList.add("wrong");
      }
    });
  }

  function onCorrect() {
    session.streak += 1;
    session.correct += 1;
    session.maxStreak = Math.max(session.maxStreak, session.streak);
    const bonus = Math.min(50, (session.streak - 1) * 2);
    session.score += 10 + bonus;
    els.feedback.textContent = session.streak > 1 ? `Correct · streak ${session.streak}` : "Correct";
    els.feedback.className = "feedback ok";
    updateHud();
  }

  function onMiss(reason) {
    session.streak = 0;
    session.missed += 1;
    els.feedback.textContent = reason;
    els.feedback.className = "feedback bad";
    updateHud();
  }

  function afterRound() {
    feedbackTimer = setTimeout(() => nextRound(), FEEDBACK_MS);
  }

  function onChoice(word, btn) {
    if (locked || !session) return;
    locked = true;
    clearTimers();
    freezeTimerBar();
    disableChoices();
    revealAnswer(word.id);

    if (word.id === session.current.target.id) {
      btn.classList.add("correct");
      onCorrect();
    } else {
      onMiss("Wrong");
    }
    afterRound();
  }

  function onTimeout() {
    if (locked || !session) return;
    locked = true;
    freezeTimerBar();
    disableChoices();
    revealAnswer(null);
    onMiss("Too slow");
    afterRound();
  }

  function startSession() {
    if (!ready) return;
    const mode = selectedMode();
    session = {
      mode,
      totalRounds: mode === "fixed" ? selectedRounds() : null,
      roundIndex: 0,
      score: 0,
      streak: 0,
      maxStreak: 0,
      correct: 0,
      missed: 0,
      current: null,
    };
    show(els.play);
    nextRound();
  }

  function endSession(reason) {
    clearTimers();
    const stats = loadStats();
    const isEndless = session.mode === "endless";
    let note = "";

    if (session.maxStreak > (stats.bestStreak || 0)) {
      stats.bestStreak = session.maxStreak;
      note = "New best streak!";
    }
    if (isEndless && session.score > (stats.bestEndlessScore || 0)) {
      stats.bestEndlessScore = session.score;
      note = note ? "New best streak & endless score!" : "New best endless score!";
    }
    saveStats(stats);
    refreshHighscores();

    els.resultsTitle.textContent =
      reason === "quit" ? "Session quit" : session.mode === "fixed" ? "Rounds complete" : "Session over";
    els.resScore.textContent = String(session.score);
    els.resStreak.textContent = String(session.maxStreak);
    els.resCorrect.textContent = String(session.correct);
    els.resMissed.textContent = String(session.missed);
    els.resNote.textContent = note;
    show(els.results);
  }

  function wireSetup() {
    document.querySelectorAll('input[name="mode"]').forEach((input) => {
      input.addEventListener("change", () => {
        els.fixedControls.classList.toggle("is-hidden", selectedMode() !== "fixed");
      });
    });

    document.querySelectorAll(".preset").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".preset").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        els.roundsInput.value = btn.dataset.rounds;
      });
    });

    els.roundsInput.addEventListener("input", () => {
      document.querySelectorAll(".preset").forEach((b) => {
        b.classList.toggle("active", b.dataset.rounds === els.roundsInput.value);
      });
    });

    els.btnStart.addEventListener("click", startSession);
    els.btnQuit.addEventListener("click", () => endSession("quit"));
    els.btnAgain.addEventListener("click", startSession);
    els.btnHome.addEventListener("click", () => {
      clearTimers();
      session = null;
      show(els.setup);
    });
  }

  async function loadWords() {
    els.btnStart.disabled = true;
    els.loadStatus.textContent = "Loading word bank…";
    try {
      const res = await fetch(window.VOCAB_SNAP.wordsUrl);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      words = data.words || [];
      byBucket = new Map();
      words.forEach((w) => {
        if (!byBucket.has(w.bucket)) byBucket.set(w.bucket, []);
        byBucket.get(w.bucket).push(w);
      });
      ready = words.length > 0;
      els.loadStatus.textContent = ready
        ? `${words.length.toLocaleString()} words ready · EN ↔ PL`
        : "Word bank empty.";
      els.btnStart.disabled = !ready;
    } catch (err) {
      console.error(err);
      els.loadStatus.textContent = "Could not load words. Refresh and try again.";
      els.btnStart.disabled = true;
    }
  }

  wireSetup();
  refreshHighscores();
  loadWords();
})();
