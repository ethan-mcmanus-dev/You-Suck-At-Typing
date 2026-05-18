# TODOS — You Suck At Typing

Deferred items from /autoplan review on 2026-05-17.
These are not in scope for the current plan (phases 1-3). Pick them up when the trigger condition is met.

---

## Post-MVP Features

### Drill Generator (phase 3b)
**Trigger:** Insights feel true on own typing and at least 2 friends have used the product.
**What:** Rule-based drill generator. Given "your SFB rate is 12%, cluster average 7%", generate
a word list overweighting bigrams involving the offending finger pair. No ML required —
bigram frequency list + filter. Transforms the product from diagnostic to training loop.
**Why deferred:** Don't build training infrastructure before validating that insights are accurate.

### Longitudinal Progress Tracking
**Trigger:** Single user has ≥5 sessions.
**What:** "Your SFB rate this month vs. last month." Session history page. Trend charts.
**Why deferred:** Requires multiple sessions from the same user. No users yet.

### Re-clustering on Real User Data
**Trigger:** 500 real user sessions accumulated in the backend.
**What:** Re-run KMeans on actual user sessions (not Aalto). Update cluster centroids in
model_artifacts with a new cluster_version. Use cluster_version column in sessions to
non-destructively migrate existing assignments.
**Why deferred:** Aalto clusters are v1; real user clusters will be better.

---

## Alternative Approaches (evaluated, not chosen)

### Browser Extension (Monkeytype Overlay)
**What:** Browser extension that captures keystrokes on Monkeytype and overlays biomechanical analysis.
**Why not now:** Re-litigates Approach A decision. Full product builds the right foundation.
Zero competition with Monkeytype, but DOM-dependency is fragile and extension complexity is high.
**Revisit if:** Approach A stalls and need a faster path to users.

### Native App (Tauri) for Rollover Precision
**What:** Native app solves the <5ms browser event ordering problem for rollover detection.
**Why not now:** Browser contingency already exists (demote rollover to secondary if unreliable).
**Revisit if:** Week 9 benchmark shows browser rollover is consistently unreliable AND
rollover is critical to the viral mechanic.

---

## Schema Improvements

### Session-Level Metadata
- `text_id UUID` — reference to a standardized test text (enables cross-user comparison on same text)
- `keyboard_layout TEXT DEFAULT 'qwerty'` — for future layout-aware labeling

---

## ML Phase (months 4+)

Per the design doc approved approach:
- Per-keystroke regression predicting (dwell, flight) distributions
- Contrastive user encoder (TypeNet-style)
- SHAP attribution for per-sequence explanations
- LLM-generated practice text targeting weak patterns
- Requires GPU or cloud training budget

Note: ML development is a personal learning goal. These are not "nice to have" — they will be built.
Track progress here as the ML phase begins.
