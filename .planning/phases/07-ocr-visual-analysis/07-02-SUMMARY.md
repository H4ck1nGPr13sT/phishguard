---
phase: 07-ocr-visual-analysis
plan: 02
subsystem: features
tags: [imagehash, opencv, perceptual-hashing, visual-features, feature-extraction, tdd]

# Dependency graph
requires:
  - phase: 07-ocr-visual-analysis
    provides: "extract_image_features(image_bytes, ocr_backend) with a marked visual-feature insertion point (Plan 07-01)"
provides:
  - "src/features/ocr/reference_brand_hashes.json + reference_hashes.py: committed perceptual-hash table (7 brands) and a lazy-imagehash loader"
  - "assets/brand_logos/build_reference_hashes.py + README.md: reproducible reference-hash builder, real-logo replacement workflow"
  - "src/features/image_features.py: perceptual_hash_similarity, _extract_layout_color_features, extract_visual_features, BRAND_MATCH_THRESHOLD, _VISUAL_FEATURE_KEYS, _default_visual_features — merged into extract_image_features"
affects: [07-03, 07-04-api-endpoint]

# Tech tracking
tech-stack:
  added: [imagehash>=4.3.2 (installed in .venv), "opencv-python-headless (requirements-only, not installed — graceful-degradation path exercised instead)"]
  patterns:
    - "Canonical feature-key-set constant (_VISUAL_FEATURE_KEYS) + a _default_visual_features() factory, used by BOTH the installed and the absent-dependency code paths, so the constant-key invariant (RESEARCH.md Pitfall 6) holds regardless of which optional heavy deps are present"
    - "Whole-function try/except ImportError around lazy cv2/imagehash imports — the entire computation body sits inside the try block, so any missing dependency degrades to defaults rather than partial/inconsistent output"
    - "Test-side _ImportBlocker (monkeypatched builtins.__import__) to deterministically simulate an absent optional dependency even when it IS installed in the current venv — makes the fallback path testable without needing a second venv"

key-files:
  created:
    - assets/brand_logos/build_reference_hashes.py
    - assets/brand_logos/README.md
    - src/features/ocr/reference_brand_hashes.json
    - src/features/ocr/reference_hashes.py
  modified:
    - src/features/image_features.py
    - tests/features/test_image_features.py

key-decisions:
  - "Reference brand tiles are deterministic Pillow-generated placeholders (solid-color vertical/horizontal bars whose width/position are derived from a hash of the brand name), not real logos — real brand assets are copyrighted and cannot be committed or fetched at build time. A developer can drop real `<brand>.png` files into assets/brand_logos/ and re-run the builder to replace any placeholder (documented in README.md)."
  - "First-draft placeholder tiles (solid color + centered text) produced IDENTICAL phash values for 4 of 7 brands, because imagehash.phash discards the DC/average frequency term — background color alone doesn't survive into the hash. Fixed by adding brand-derived structural variation (bar width/position), which produced pairwise Hamming distances of 16-38 across all 7 brands, comfortably above BRAND_MATCH_THRESHOLD."
  - "perceptual_hash_similarity and _extract_layout_color_features each wrap their ENTIRE body (not just the import line) in try/except ImportError, returning the exact default sub-dict on failure — this, combined with extract_visual_features always merging under _default_visual_features(), is what guarantees the constant _VISUAL_FEATURE_KEYS set with or without cv2/imagehash installed."

patterns-established:
  - "Pattern: whole-body try/except ImportError for optional heavy-dependency feature functions, paired with a canonical default-values factory merged first, so partial computation never produces a partial key set."
  - "Pattern: _ImportBlocker test helper (monkeypatched builtins.__import__) for deterministically testing dependency-absence code paths regardless of the test venv's actual installed packages."

requirements-completed: [INPUT-07]

# Metrics
duration: 4min
completed: 2026-09-30
---

# Phase 7 Plan 02: OCR & Visual Analysis — Perceptual-Hash Brand Similarity & Layout Heuristics Summary

**Perceptual-hash brand similarity (imagehash.phash + committed 7-brand reference table) and OpenCV edge/color/contour layout heuristics, merged into extract_image_features with a guaranteed-constant key set whether or not cv2/imagehash are installed.**

## Performance

- **Duration:** ~4 min (measured from first to last task commit; excludes read/planning time)
- **Started:** 2026-09-30T15:09:55+02:00 (Task 1 commit)
- **Completed:** 2026-09-30T15:13:55+02:00 (Task 2 GREEN commit)
- **Tasks:** 2 completed
- **Files modified:** 6 (2 modified, 4 created)

## Accomplishments
- `assets/brand_logos/build_reference_hashes.py` generates deterministic, structurally-distinct per-brand placeholder tiles (Pillow-only, no network/copyright dependency) and computes `imagehash.phash` for each — the committed `src/features/ocr/reference_brand_hashes.json` covers 7 brands (paypal, microsoft, apple, google, amazon, bank_of_america, chase) with pairwise Hamming distances of 16-38, confirming the hashes are genuinely distinguishable, not collided.
- `src/features/ocr/reference_hashes.py` provides `load_reference_hashes()`: reads the committed JSON, lazily imports `imagehash` inside the function, caches the parsed `{brand: ImageHash}` table in a module singleton, and raises `ImportError` cleanly when `imagehash` is absent (never crashes on import of the module itself).
- `src/features/image_features.py` gained `perceptual_hash_similarity`, `_extract_layout_color_features`, and `extract_visual_features`, all following the mandatory whole-body try/except ImportError pattern — verified empirically: with `cv2` (never installed in this venv) AND `imagehash` (installed, but simulated absent via a test-side `_ImportBlocker`) both blocked, `extract_visual_features` still returns the full 5-key `_VISUAL_FEATURE_KEYS` set with documented defaults (`visual_hash_distance=64.0`, all others `0.0`) and raises no exception.
- `extract_image_features` now returns OCR-text features + visual features in one all-numeric dict whose key set is empirically confirmed identical: (a) across a text-bearing vs. blank image, (b) with cv2/imagehash present vs. simulated-absent — closing RESEARCH.md Pitfall 6 for the visual-feature path.
- 7 new unit tests added (12 total in the file): a real self-match test (`paypal` tile → its own stored hash → distance 0, `imagehash` actually installed for this), an OpenCV-heuristic-range test (skips cleanly, `cv2` not installed), and 5 dependency-absence/constant-key tests that always run.
- Full project test suite: 399 passed, 2 skipped, 47s — no regressions, still fully torch-free.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build committed reference brand-hash asset and loader** - `80a8914` (feat)
2. **Task 2: Implement visual features and merge into extract_image_features (TDD)**
   - RED: `0e47f62` (test) — failing tests committed first, confirmed `ImportError: cannot import name 'BRAND_MATCH_THRESHOLD'` before implementation existed
   - GREEN: `2521632` (feat) — implementation added, all 12 tests pass (1 skip, cv2 absent), full suite green

_TDD task (Task 2) produced two commits (test → feat) per the RED/GREEN gate. No REFACTOR commit was needed — implementation matched the interface contract on first pass._

## Files Created/Modified
- `assets/brand_logos/build_reference_hashes.py` - Reproducible builder: deterministic per-brand placeholder tiles + `imagehash.phash`, prefers a real `<brand>.png` if dropped into the directory
- `assets/brand_logos/README.md` - Documents the placeholder/real-logo replacement workflow and the tunable-threshold caveat (RESEARCH.md Pitfall 5)
- `src/features/ocr/reference_brand_hashes.json` - Committed source-of-truth hash table (7 brands incl. paypal)
- `src/features/ocr/reference_hashes.py` - `load_reference_hashes()`: lazy-imagehash loader with module-level singleton cache
- `src/features/image_features.py` - `BRAND_MATCH_THRESHOLD`, `_VISUAL_FEATURE_KEYS`, `_default_visual_features`, `perceptual_hash_similarity`, `_extract_layout_color_features`, `extract_visual_features`; wired into `extract_image_features` at the Plan 07-01 insertion point
- `tests/features/test_image_features.py` - `_ImportBlocker` test helper + 7 new visual-feature tests (installed-path + always-run fallback)

## Decisions Made
- Rebuilt the placeholder-tile generator mid-task after discovering 4 of 7 brands produced identical phash values (solid background color alone doesn't survive `imagehash.phash`, which discards the DC/average term) — added brand-derived bar-width/position structure so all 7 hashes are pairwise distinct (min distance 16, well above `BRAND_MATCH_THRESHOLD=10`). See key-decisions in frontmatter for detail.
- Used a monkeypatched-`builtins.__import__` `_ImportBlocker` test helper rather than relying on the deps simply not being installed, so the absent-dependency fallback path is exercised deterministically regardless of what happens to be in the venv (e.g. `imagehash` IS installed here, but the fallback test still proves the degrade-gracefully code path works).
- Kept `perceptual_hash_similarity`'s numeric-only return separate from the closest-brand label (returned as the second tuple element), per the plan's explicit interface — keeps the numeric feature dict free of any non-numeric value, consistent with the all-numeric contract the ensemble model expects.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed colliding placeholder-tile perceptual hashes**
- **Found during:** Task 1, immediately after first builder run
- **Issue:** The plan's placeholder-tile design (solid brand-color background + centered text) produced identical `imagehash.phash` values for `amazon`, `chase`, `google`, and `paypal` (all `f8f80707f8f80707`) — because `imagehash.phash` discards the DC/average frequency component, so background color differences alone don't survive into the hash, and the small default-font text contributed too little low-frequency signal to differentiate. This would have made `visual_brand_similarity_flag` unreliable (multiple brands indistinguishable) and violated the builder's own docstring claim that "each brand's placeholder differs from the others."
- **Fix:** Added deterministic brand-derived structural variation to `_placeholder_tile` — a vertical color bar (width) and horizontal color band (height + vertical offset), both computed from a hash of the brand name, so each brand's low-frequency DCT structure differs meaningfully. Re-ran the builder; verified all 7 pairwise Hamming distances are now 16-38 (previously several were 0).
- **Files modified:** assets/brand_logos/build_reference_hashes.py, src/features/ocr/reference_brand_hashes.json
- **Verification:** Manual pairwise-distance check across all 7 brands (`imagehash.hex_to_hash` + `__sub__`), all distances >= 16; Task 1's automated verify (`HASHES_OK 7`, `paypal` present) still passes.
- **Committed in:** `80a8914` (Task 1 commit — the collision was caught and fixed before the first commit, so no separate fix commit was needed)

---

**Total deviations:** 1 auto-fixed (1 bug — placeholder-tile hash collision caught before commit)
**Impact on plan:** No architectural or scope impact; the fix was contained entirely within the builder script's tile-generation logic, matching the plan's own intent ("distinct per brand so hashes differ") more faithfully than the plan's illustrative description implied.

## Issues Encountered
None beyond the auto-fixed hash-collision issue documented above.

## User Setup Required
None - no external service configuration required. Note: `imagehash` is now installed in the project `.venv` (lightweight — pulled only `PyWavelets`, no torch); `opencv-python-headless`/`easyocr`/`torch` remain declared in `requirements.txt` but NOT installed, per the mandatory dependency-isolation constraint. The OpenCV-heuristic-range test (`test_layout_color_heuristics_ranges`) will start running (rather than skipping) once `opencv-python-headless` is installed in a future plan/session.

## Next Phase Readiness
- `extract_image_features(image_bytes, ocr_backend)` now returns the full OCR-text + visual feature set with a proven-constant key set, ready for Plan 07-04's `/predict/image` API endpoint and any image-ensemble training script to consume directly.
- `extract_visual_features(image)` and `perceptual_hash_similarity(image, reference_hashes)` are stable public entry points if a later plan wants to surface the closest-brand label (e.g., in a human-readable explanation string) — currently kept out of the numeric dict by design, available as the second tuple element.
- `BRAND_MATCH_THRESHOLD` and the reference hash table are both explicitly flagged (code comment + README) as unvalidated/tunable — a future plan doing real dataset evaluation should revisit both per RESEARCH.md Pitfall 5 before any thesis claim relies on them.
- No blockers. Full suite remains torch-free (399 passed, 2 skipped) after this plan's changes.

---
*Phase: 07-ocr-visual-analysis*
*Completed: 2026-09-30*

## Self-Check: PASSED

All 7 claimed files found on disk; all 3 claimed commit hashes (80a8914, 0e47f62, 2521632) found in `git log --oneline --all`.
