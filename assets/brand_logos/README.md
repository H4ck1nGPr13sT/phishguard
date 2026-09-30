# Brand Reference Assets (Phase 7 — Visual Feature Analysis)

This directory sources the reference perceptual hashes used by
`perceptual_hash_similarity()` (`src/features/image_features.py`) to flag
visual similarity between an uploaded image and commonly-phished brands
(INPUT-07).

## Current state: placeholder tiles

Real brand logos/login-page screenshots are **not** committed to this repo
(copyright + no network access at build time). Instead,
`build_reference_hashes.py` generates a deterministic Pillow placeholder
tile per brand — a solid brand-associated background color plus the brand
name drawn as text — and computes `imagehash.phash()` of that placeholder.
The resulting hashes are internally consistent (each brand's placeholder
differs from every other brand's) but they are **stand-ins**, not real-world
matches: hashing an actual PayPal login screenshot will NOT necessarily be
close (Hamming distance) to the `paypal` entry in
`src/features/ocr/reference_brand_hashes.json` today.

Curated brand list: `paypal`, `microsoft`, `apple`, `google`, `amazon`,
`bank_of_america`, `chase`.

## Replacing a placeholder with a real reference image

1. Obtain a real login-page screenshot or logo for the brand, **only from
   sources you have the legitimate right to use** for this purpose.
2. Save it as `<brand>.png` in this directory, e.g.
   `assets/brand_logos/paypal.png` (must match a key in `BRAND_COLORS`
   inside `build_reference_hashes.py`, or add a new entry there first).
3. Re-run the builder:
   ```bash
   .venv/bin/pip install imagehash   # lightweight — only pulls Pillow/numpy
   .venv/bin/python assets/brand_logos/build_reference_hashes.py
   ```
   The builder automatically prefers a real `<brand>.png` in this directory
   over the generated placeholder for that brand.
4. Commit the regenerated `src/features/ocr/reference_brand_hashes.json`.

## The match threshold is tunable — not a fixed fact

`BRAND_MATCH_THRESHOLD` (in `src/features/image_features.py`) is a Hamming
distance cutoff on a 64-bit perceptual hash (`imagehash.phash`), currently
set to `10` as a starting point cited from common `imagehash` usage
conventions — **not** empirically derived for this project's data. Per
`07-RESEARCH.md` Pitfall 5, this value must be validated empirically against
a real phishing-image dataset (once dataset acquisition/labeling work makes
one available) before being treated as a load-bearing detection threshold in
any evaluation or thesis claim. Until then, treat `visual_brand_similarity_flag`
as an illustrative, tunable heuristic signal, not a calibrated classifier.

## Reproducibility

`build_reference_hashes.py` is deterministic and re-runnable: given the same
curated brand list and the same (placeholder or real) input tiles, it always
produces the same output JSON. It is a **build-time-only** tool — it is
never imported by application code or by the fast unit-test suite, and
`imagehash` is not a hard runtime dependency of the loader path (see
`src/features/ocr/reference_hashes.py`, which raises `ImportError` cleanly
if `imagehash` is absent).
