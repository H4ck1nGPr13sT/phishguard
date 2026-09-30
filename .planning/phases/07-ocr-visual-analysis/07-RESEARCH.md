# Phase 7: OCR & Visual Analysis - Research

**Researched:** 2026-09-30
**Domain:** Image-based phishing detection — OCR text extraction + visual similarity analysis
**Confidence:** MEDIUM-HIGH (stack verified via registry + slopcheck; timing/perf figures are CITED from vendor docs, not benchmarked in this environment)

## Summary

Phase 7 adds image input (PNG/JPG/screenshots) as a third content modality alongside URL and email/SMS. The work splits into two independent signal sources that get combined: (1) **OCR text extraction** (EasyOCR, PyTorch-backed) whose output is fed into the **existing** `TextFeatureExtractor` / text-features pipeline rather than a new classifier, and (2) **visual features** — perceptual-hash brand similarity (`imagehash`) plus lightweight layout/color heuristics (OpenCV) — which are genuinely new signal. This mirrors the Phase 6 pattern: a new `image_features.py` module registered in `extractors.py`'s `ContentType` enum, a new Pydantic request/response pair, and a new `/predict/image` endpoint, with the same `EmailSMSResponse`-style aggregation via `MultiParadigmAggregator`.

The dominant risk is **not** the OCR/vision algorithms themselves but the **dependency footprint**: EasyOCR pulls in PyTorch + torchvision (~700MB+ download, GPU-optional, CPU-mode works fine but reader init + first inference take several seconds and downloads ~64MB/language model files to `~/.EasyOCR/model` on first use). None of `easyocr`, `torch`, `opencv-python-headless`, or `imagehash` are installed in the project `.venv` today (confirmed: only Pillow 12.1.1 and numpy 2.4.2 present). Since the existing ~389-test suite must stay fast and CI-friendly, the module MUST be built so it imports and unit-tests cleanly with these heavy libraries **absent** — via a pluggable/mockable OCR backend interface, lazy (first-call, not import-time) model loading, and graceful degradation (structured "OCR unavailable" result, not a crash) when the backend can't be loaded. The <500ms API constraint that Phase 6 satisfied via startup-time model loading (see `src/api/main.py` lifespan) **cannot** be satisfied the same way for OCR inference itself (typically 200ms-3s+ per image on CPU) — the phase must document this explicitly as a scope/contract decision (async processing + polling, or documented exception to the <500ms rule for the image endpoint specifically) rather than silently violating it.

**Primary recommendation:** Add `easyocr` behind a small `OCRBackend` protocol/interface with a `NullOCRBackend` fallback; extract images synchronously in the request handler for MVP but return quickly by loading the EasyOCR reader once at app-startup (like the ML models) and cache per-image-hash OCR results; treat perceptual-hash brand similarity as the primary visual signal (cheap, deterministic, testable without torch) and CNN embeddings as explicitly out of scope / a stretch goal given the academic timeline. Feed OCR'd text into the existing `TextFeatureExtractor`, not a new NLP path.

## User Constraints

No CONTEXT.md exists for this phase (not yet run through `/gsd:discuss-phase`). The following are locked by upstream project docs (PROJECT.md, ROADMAP.md) and are treated as constraints:

### Locked Decisions (from PROJECT.md Key Decisions table + ROADMAP.md Phase 7)
- OCR must use **EasyOCR** specifically (named in ROADMAP.md Phase 7 goal and REQUIREMENTS INPUT-06) — not Tesseract as primary.
- "OCR + cechy wizualne dla obrazów" (OCR + visual features) is a named core-value decision in PROJECT.md — both signals are required, not optional.
- Visual similarity: **perceptual hashing OR CNN embeddings** — ROADMAP.md leaves the choice open ("using perceptual hashing or CNN embeddings"). This is Claude's discretion (see below).
- Must combine OCR text analysis with visual feature analysis for a "final verdict" (Success Criterion 5) — implies feeding into the existing multi-paradigm aggregation, consistent with Phase 5/6 architecture.
- <500ms API response requirement is stated as a system-wide constraint (echoed from Phase 2/6 `main.py` lifespan comments: "CRITICAL: Model is loaded ONCE at startup... sub-500ms response times"). Phase 7 must explicitly reconcile this with OCR's inherent latency (see Common Pitfalls and Architecture Patterns below).
- Open demo, no auth (PROJECT.md Out of Scope) — image upload endpoint needs no auth, but does need file-size/type validation like the existing `.eml` upload endpoint (5MB limit pattern in `predict_email_file`).
- Academic/interpretability context (PROJECT.md): explanations must be human-readable, consistent with `EmailSMSResponse.explanation` pattern.

### Claude's Discretion
- Perceptual hashing (`imagehash`) vs. CNN embeddings for brand-similarity — **recommend perceptual hashing** for this phase (see Standard Stack rationale); CNN embeddings noted as future-work/stretch in Open Questions.
- Whether OCR runs fully synchronously in-request vs. background task/job-queue — **recommend synchronous-with-caching for MVP**, given no existing task-queue infrastructure (no Celery/RQ/Redis anywhere in the codebase) and the academic-demo scope; document the <500ms tradeoff transparently rather than building new infra.
- Fallback OCR engine (pytesseract via system `tesseract`) — **recommend as a documented fallback/dev-mode path**, not the primary path, since `tesseract` binary is present in this dev environment (`/opt/homebrew/bin/tesseract`) but is not guaranteed on grading/deployment machines and is not what ROADMAP.md/INPUT-06 names.
- Exact layout/color heuristics for "suspicious UI elements" (Success Criterion 2) — no existing pattern to mirror; recommend a small, interpretable, testable heuristic set (see Architecture Patterns).

### Deferred Ideas (OUT OF SCOPE for Phase 7)
- CSV batch processing of images — belongs to Phase 8 (Batch Processing & Web Interface), do not build batch image upload here.
- Web UI for image upload — belongs to Phase 8.
- SHAP/LIME explainability for image features — belongs to Phase 9 (Explainability & Dashboard).
- Production-grade async job queue (Celery/RQ) — not justified by academic-demo scale; revisit only if Phase 8's web UI needs it.
- GPU acceleration / CUDA setup — no evidence of GPU in target environment; EasyOCR must run `gpu=False`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INPUT-04 | System przyjmuje obraz do analizy (PNG, JPG, screenshot) | New `/predict/image` FastAPI endpoint using `UploadFile`, mirroring `predict_email_file` pattern (file-type + size validation, `python-multipart` already installed). Pillow (already installed) validates/opens the image. |
| INPUT-06 | System ekstrahuje tekst z obrazów poprzez OCR (EasyOCR) | `easyocr.Reader(['en'], gpu=False)` wrapped in a lazy-loaded, mockable `OCRBackend` interface; extracted text piped into existing `TextFeatureExtractor.extract_all_features()` — no new NLP code needed. |
| INPUT-07 | System analizuje cechy wizualne obrazów (układ, logo, elementy graficzne) | New `image_features.py`: perceptual hash (`imagehash.phash`) diffed against a small reference-logo hash table for brand similarity; OpenCV-based (or Pillow-only, see Alternatives) heuristics for layout/color/suspicious-UI-element detection. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Image upload & validation (type/size) | API / Backend | — | Mirrors existing `UploadFile` pattern in `endpoints.py`; no client-side tier exists (API-only project, no web UI yet — that's Phase 8) |
| OCR text extraction (EasyOCR) | API / Backend (feature-extraction module) | — | CPU-bound inference; runs in-process like spaCy/TextFeatureExtractor, not a separate service |
| OCR-extracted text → linguistic features | API / Backend | — | Reuses existing `TextFeatureExtractor` — same tier as email/SMS text features (Phase 6) |
| Visual similarity (perceptual hash) | API / Backend (feature-extraction module) | — | Pure computation, no external service; belongs beside `image_features.py` |
| Layout/color/UI heuristics | API / Backend | — | Same tier, same module |
| Multi-paradigm aggregation of image verdict | API / Backend | — | Reuses `MultiParadigmAggregator` exactly as Phase 6 does for email/SMS |
| Reference brand-logo hash storage | Database / Storage (flat file/joblib cache) | — | Small static reference set (logos of common phished brands), loaded like `models/` artifacts via `joblib`/`cache.py` pattern — no need for a real DB given academic-demo scale |
| Model/reader warm-loading | API / Backend (FastAPI lifespan) | — | Same mechanism as `ml_models` dict in `main.py`; EasyOCR reader added to lifespan startup, NOT per-request |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| easyocr | 1.7.2 [VERIFIED: PyPI registry] | OCR text extraction from images | Named explicitly in ROADMAP.md/INPUT-06; deep-learning based (CRAFT detector + CRNN recognizer), 80+ languages, actively maintained (JaidedAI/EasyOCR on GitHub), pure-Python API `Reader(['en']).readtext(image)` |
| torch | 2.8.0 [VERIFIED: PyPI registry] | Backend inference engine required by EasyOCR | Hard transitive dependency of easyocr — not optional. CPU-only wheels work fine (`gpu=False`) |
| torchvision | (pulled transitively, 0.23.0 observed) [VERIFIED: PyPI registry] | Transitive dependency of easyocr | Auto-installed with easyocr; no direct use in project code |
| imagehash | 4.3.2 [VERIFIED: PyPI registry] | Perceptual hashing for visual brand similarity | Standard, lightweight (~small footprint, only needs Pillow + numpy + PyWavelets), widely used for near-duplicate/phishing-clone detection research (see PhishSnap paper, arXiv:2512.02243, MEDIUM confidence — single paper) |
| opencv-python-headless | already present, 4.12.0.88 [VERIFIED: pip list — already installed] | Layout/color analysis, image preprocessing for OCR (denoise, contrast, deskew) | `-headless` variant avoids GUI/Qt deps (correct choice for a server; do NOT install plain `opencv-python`) |
| Pillow | already present, 12.1.1 [VERIFIED: pip list] | Image loading/validation/format conversion | Already a project dependency; used to validate uploaded file is a real image before handing to OCR/CV |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytesseract | 0.3.13 [VERIFIED: PyPI registry] | Fallback/lightweight OCR engine | Optional secondary backend behind the same `OCRBackend` interface; useful for fast unit tests or environments where torch is undesirable. Requires system `tesseract` binary (present in dev env at `/opt/homebrew/bin/tesseract`, NOT guaranteed elsewhere — must be an explicit fallback, not a silent default) |
| numpy | already present, 2.4.2 [VERIFIED: pip list] | Array interop between Pillow/OpenCV/EasyOCR | Already required project-wide |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| EasyOCR (torch-based) | pytesseract (Tesseract wrapper) | Much lighter (no torch, ~10MB vs 700MB+), faster cold-start, but lower accuracy on stylized/low-contrast phishing screenshots and requires a system binary dependency instead of pure pip install. Not the requirement-specified engine — keep as fallback only. |
| EasyOCR | Cloud OCR API (Google Vision, AWS Textract) | Higher accuracy, zero local dependency weight, but introduces network calls, API keys/cost, and breaks the "open demo, no external accounts" academic-project framing (PROJECT.md constraints say public datasets only, no commercial data access implied preference for self-hosted). Rejected. |
| imagehash perceptual hashing | CNN embeddings (e.g., a pretrained ResNet/CLIP for logo similarity) | CNN embeddings are more robust to cropping/rotation but require another heavy model download, GPU benefits, and much more code/complexity for a metric (embedding similarity threshold) that's harder to justify/interpret in an academic write-up than Hamming distance on a perceptual hash. ROADMAP.md explicitly allows either — perceptual hashing is the pragmatic choice for this phase; CNN embeddings can be framed as "future work" in the thesis. |
| OpenCV for layout heuristics | Pillow-only (no OpenCV) | OpenCV is already installed (used previously — appears in pip list already, likely a transitive dep of scikit-image from Phase 6). Using it for edge detection / color histograms / contour-based "form-like structure" heuristics is more capable than Pillow alone. Keep OpenCV, since it costs nothing extra to install. |

**Installation:**
```bash
# Add to requirements.txt under a new "# Phase 7 - OCR & Visual Analysis" section:
pip install easyocr>=1.7.2 imagehash>=4.3.2 opencv-python-headless>=4.12.0 pytesseract>=0.3.13
```

**Version verification performed:** `pip index versions <pkg>` run against live PyPI on 2026-09-30 (see Package Legitimacy Audit below) confirmed: easyocr 1.7.2 (latest), imagehash 4.3.2 (latest), pytesseract 0.3.13 (latest), torch 2.8.0 (latest), opencv-python-headless already installed at 4.12.0.88 (latest is 5.0.0.93 — a major version bump; **recommend pinning to the currently-installed 4.x line** to avoid an untested breaking upgrade mid-thesis, unless the planner deliberately wants to test 5.0).

## Package Legitimacy Audit

`slopcheck` (v0.6.1) was installed and run against all six candidate packages via `slopcheck install easyocr opencv-python-headless imagehash pytesseract torch Pillow` (installs + checks in one step; no `--json` support in this version, output parsed from CLI table).

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| easyocr | PyPI | mature (first released ~2020, 1.7.x since 2023) | high (standard OCR lib) | github.com/JaidedAI/EasyOCR | [OK] | Approved |
| torch | PyPI | mature (2016+) | very high | github.com/pytorch/pytorch | [OK] | Approved |
| torchvision | PyPI | mature, transitive dep of easyocr | very high | github.com/pytorch/vision | [OK] (not directly scanned; official PyTorch project, transitively pulled) | Approved (transitive) |
| opencv-python-headless | PyPI | mature | very high | github.com/opencv/opencv-python | [OK] | Approved |
| imagehash | PyPI | mature (2013+) | moderate-high | github.com/JohannesBuchner/imagehash | [OK] | Approved |
| pytesseract | PyPI | mature (2010+) | high | github.com/madmaze/pytesseract | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

No `postinstall`-style script risk applies (Python ecosystem, `pip`, no npm postinstall analog beyond `setup.py`/build backends — all six are long-established, widely-mirrored packages).

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────┐
Client ──POST──────▶│ /predict/image (FastAPI)     │
 (PNG/JPG           │  1. validate file type/size  │
  bytes)             │  2. Pillow: open + verify     │
                    └──────────────┬───────────────┘
                                   │ PIL.Image
                     ┌─────────────┼─────────────────┐
                     ▼                                ▼
         ┌───────────────────────┐      ┌───────────────────────────┐
         │  OCR path              │      │  Visual-feature path       │
         │  image_features.py      │      │  image_features.py          │
         │  ┌───────────────────┐ │      │  ┌───────────────────────┐ │
         │  │ preprocess()       │ │      │  │ perceptual_hash()      │ │
         │  │ (OpenCV: denoise,  │ │      │  │ vs. reference brand     │ │
         │  │  contrast, resize) │ │      │  │ hash table              │ │
         │  └─────────┬─────────┘ │      │  └───────────┬───────────┘ │
         │            ▼            │      │              ▼             │
         │  ┌───────────────────┐ │      │  ┌───────────────────────┐ │
         │  │ OCRBackend.read()  │ │      │  │ layout/color heuristics│ │
         │  │ (EasyOCR reader,   │ │      │  │ (OpenCV contours,       │ │
         │  │  lazy-loaded once) │ │      │  │  histograms)             │ │
         │  └─────────┬─────────┘ │      │  └───────────┬───────────┘ │
         └────────────┼───────────┘      └──────────────┼─────────────┘
                       ▼                                  ▼
           extracted_text (str)                visual_features (dict)
                       │                                  │
                       ▼                                  │
        ┌──────────────────────────────┐                  │
        │ TextFeatureExtractor           │                  │
        │ .extract_all_features(text)    │  (EXISTING,       │
        │ (existing Phase 6 module)      │   unchanged)       │
        └──────────────┬─────────────────┘                  │
                       │ text_features (dict)                │
                       └─────────────┬────────────────────────┘
                                     ▼
                      ┌───────────────────────────────┐
                      │ image_ensemble model            │
                      │ predict_proba(combined features)│
                      │  (mirrors email_ensemble /       │
                      │   sms_ensemble pattern)          │
                      └───────────────┬───────────────────┘
                                     ▼
                      ┌───────────────────────────────┐
                      │ MultiParadigmAggregator          │
                      │ .aggregate(ml, rules, bayesian)  │
                      │  (EXISTING, unchanged)            │
                      └───────────────┬───────────────────┘
                                     ▼
                          EmailSMSResponse-like JSON
                          (content_type="image")
```

### Recommended Project Structure
```
src/features/
├── image_features.py       # NEW: extract_image_features(), OCRBackend interface,
│                            #      preprocess(), perceptual_hash_similarity(),
│                            #      layout/color heuristics
├── extractors.py            # MODIFIED: add ContentType.IMAGE, dispatch to image_features
└── ocr/                      # NEW subpackage (keeps heavy-dep code isolated)
    ├── __init__.py
    ├── backend.py            # OCRBackend Protocol + EasyOCRBackend + NullOCRBackend
    └── reference_hashes.py   # Small static table of known-brand logo perceptual hashes

src/api/
├── endpoints.py              # MODIFIED: add POST /predict/image
├── models.py                 # MODIFIED: add ImageRequest/Response (or reuse UploadFile pattern)
└── main.py                   # MODIFIED: lifespan loads OCRBackend once (like ml_models)

tests/features/
└── test_image_features.py    # NEW: uses NullOCRBackend / a fake reader — NO torch import required

tests/integration/
└── test_image_integration.py # NEW: marked slow/optional, skipped unless easyocr installed
```

### Pattern 1: Pluggable, Lazy-Loaded OCR Backend (mockable, no forced torch import)
**What:** Define a small `OCRBackend` interface (Protocol or ABC) with a `read_text(image) -> str` method. Provide `EasyOCRBackend` (imports `easyocr` lazily inside `__init__`, not at module top level) and a `NullOCRBackend` that returns `""` with a logged warning. The feature-extraction function accepts an injected backend (default: a module-level singleton resolved lazily, same pattern as `get_text_extractor()` in `extractors.py`).
**When to use:** Always — this is the core pattern that keeps the test suite fast and torch-optional.
**Example:**
```python
# src/features/ocr/backend.py
from typing import Protocol
import logging

logger = logging.getLogger(__name__)


class OCRBackend(Protocol):
    def read_text(self, image) -> str: ...


class NullOCRBackend:
    """Fallback used when easyocr/torch is not installed or fails to load.
    Returns empty text; downstream text-feature extraction degrades gracefully
    (all-zero linguistic features) rather than crashing the request.
    """
    def read_text(self, image) -> str:
        logger.warning("OCR backend unavailable — returning empty text")
        return ""


class EasyOCRBackend:
    """Lazy-loaded EasyOCR wrapper. Reader is created on first use (or via
    explicit warm_up()) and cached on the instance — mirrors the singleton
    pattern used for TextFeatureExtractor/spaCy in extractors.py.
    """
    def __init__(self, languages=("en",), gpu: bool = False):
        self._languages = list(languages)
        self._gpu = gpu
        self._reader = None  # NOT loaded at __init__ — loaded on first read_text()

    def _get_reader(self):
        if self._reader is None:
            import easyocr  # local import — heavy dep isolated here
            self._reader = easyocr.Reader(self._languages, gpu=self._gpu, verbose=False)
        return self._reader

    def read_text(self, image) -> str:
        reader = self._get_reader()
        # readtext returns list of (bbox, text, confidence)
        results = reader.readtext(image, detail=1)
        return " ".join(text for _, text, conf in results if conf > 0.3)


def resolve_ocr_backend() -> "OCRBackend":
    """Factory: try EasyOCR, fall back to Null. Used by FastAPI lifespan
    and by extractors.py's module-level singleton getter."""
    try:
        import easyocr  # noqa: F401  — import-only availability check
        return EasyOCRBackend()
    except ImportError:
        return NullOCRBackend()
```

### Pattern 2: OCR Text Feeds the EXISTING Text Pipeline (don't reimplement NLP)
**What:** Once `OCRBackend.read_text()` returns a string, pass it straight into `get_text_extractor().extract_all_features(text)` (the same singleton spaCy-backed extractor used for email/SMS in Phase 6). Prefix resulting keys `ocr_text_*` for feature-name disambiguation, matching the `text_*` prefix convention already used in `extract_email_features`.
**When to use:** Always — this satisfies Success Criterion 5 ("combines OCR-extracted text analysis with visual feature analysis") without duplicating NLP logic.
**Example:**
```python
# src/features/image_features.py
from src.features.extractors import get_text_extractor

def extract_image_features(image_bytes: bytes, ocr_backend: "OCRBackend") -> dict:
    image = _load_and_validate_image(image_bytes)          # Pillow, raises on invalid
    preprocessed = _preprocess_for_ocr(image)                # OpenCV: grayscale, denoise, upscale if small
    ocr_text = ocr_backend.read_text(preprocessed)

    text_extractor = get_text_extractor()
    text_features = text_extractor.extract_all_features(ocr_text)
    text_features_prefixed = {f"ocr_text_{k}": v for k, v in text_features.items()}

    visual_features = _extract_visual_features(image)        # perceptual hash + layout/color heuristics

    return {**text_features_prefixed, **visual_features, "ocr_char_count": len(ocr_text)}
```

### Pattern 3: Perceptual-Hash Brand Similarity (interpretable, testable, no torch)
**What:** Precompute `imagehash.phash()` for a small curated set of reference brand assets (login-page screenshots / logos of commonly-phished brands — PayPal, banks, Microsoft, Google, etc. — sourced from public data the same way Phase 1 sourced phishing datasets). At inference time, compute the uploaded image's phash and its Hamming distance to each reference; report the closest match and distance as `visual_brand_match` / `visual_brand_similarity_score`.
**When to use:** Primary visual-similarity technique for Phase 7 (per Claude's Discretion above).
**Example:**
```python
# Source: imagehash library docs (github.com/JohannesBuchner/imagehash) — CITED
import imagehash
from PIL import Image

def perceptual_hash_similarity(image: Image.Image, reference_hashes: dict[str, imagehash.ImageHash]) -> dict:
    query_hash = imagehash.phash(image)
    distances = {brand: query_hash - ref_hash for brand, ref_hash in reference_hashes.items()}
    closest_brand = min(distances, key=distances.get)
    closest_distance = distances[closest_brand]
    # Hamming distance on a 64-bit phash: 0 = identical, >10-15 = visually distinct (CITED: common imagehash usage threshold, MEDIUM confidence — no single canonical source pins this number; treat as tunable and document in thesis)
    return {
        "visual_closest_brand": closest_brand,
        "visual_hash_distance": closest_distance,
        "visual_brand_similarity_flag": int(closest_distance <= 10),
    }
```

### Pattern 4: Startup-Time Warm Loading (reconciling OCR latency with the <500ms goal)
**What:** Extend `src/api/main.py`'s `lifespan` to construct the `EasyOCRBackend` and call a `warm_up()` method (a `read_text()` call on a tiny blank image) once at process startup, exactly like `ml_models["phishing_detector"]` is loaded once. This removes the multi-second **model-load** cost from the request path — but does NOT remove the **per-image inference** cost (detection + recognition on the actual uploaded image), which is inherently proportional to image size/complexity and typically **exceeds 500ms on CPU** even with a warm model.
**When to use:** Always for the reader/model; document the inference-time exception explicitly (see Common Pitfalls).
**Example:**
```python
# src/api/main.py (addition to lifespan)
from src.features.ocr.backend import resolve_ocr_backend

@asynccontextmanager
async def lifespan(app: FastAPI):
    ...
    ml_models["ocr_backend"] = resolve_ocr_backend()
    if hasattr(ml_models["ocr_backend"], "_get_reader"):
        ml_models["ocr_backend"]._get_reader()  # force model download/load now, not on first request
    yield
```

### Anti-Patterns to Avoid
- **Importing `easyocr` at module top-level in `image_features.py` or `extractors.py`:** This forces torch import (and its ~1-2s import cost, plus hard install requirement) onto every test run and every `ContentType` dispatch, even for URL/email/SMS requests. Always import lazily inside the backend class.
- **Creating a new `easyocr.Reader(...)` per request:** Reader construction loads model weights from disk (or downloads them on first-ever run) — this is the single biggest latency trap. Must be a singleton (lifespan-loaded or lazily-cached, never per-call).
- **Building a full custom async job queue (Celery/Redis) for "asynchronous OCR processing" when nothing else in the codebase uses one:** Success Criterion 3 says "handles OCR processing asynchronously to avoid blocking" — interpret this primarily as "don't block the FastAPI event loop" (i.e., use `async def` + `run_in_threadpool`, which FastAPI already does automatically for sync `def` endpoints — see `predict_sms`'s comment: "FastAPI runs sync functions in threadpool automatically"), not as "stand up new infrastructure." A real background-job/polling API is legitimate future work for Phase 8's web UI but is disproportionate for this phase's scope.
- **Re-implementing phishing text classification on OCR text with new code:** Success Criterion 5 wants OCR text analysis "combined" with visual analysis — the existing `TextFeatureExtractor` + `email_ensemble`-style model already does text classification; reuse it.
- **Hand-rolling a Hamming-distance/bit-count function for perceptual hash comparison:** `imagehash.ImageHash.__sub__` already implements this correctly and efficiently — don't reimplement.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text extraction from images | Custom CNN/OCR pipeline | EasyOCR (`easyocr.Reader.readtext`) | Requirement-mandated (INPUT-06); building a competitive OCR model from scratch is out of scope for a phishing-detection thesis and would take the project off its actual research question |
| Perceptual/near-duplicate image comparison | Custom DCT-hash or pixel-diff function | `imagehash` (phash/dhash/average_hash) | Well-tested reference implementation; hand-rolled DCT hashing is a classic source of off-by-one/normalization bugs |
| Image format validation (is this really a PNG/JPG, not a disguised file) | Manual magic-byte sniffing | `PIL.Image.open(...).verify()` | Pillow already handles this correctly and is already a dependency; magic-byte checks alone don't catch truncated/corrupt image data the way `Image.verify()` does |
| Linguistic feature extraction from OCR'd text | New NLP feature set for images | Existing `TextFeatureExtractor` (Phase 6) | Text is text regardless of source — reusing the pipeline is both less code and a stronger thesis argument for the "multi-paradigm synergy" core value in PROJECT.md |
| Threading/async offload for CPU-bound inference | Manual `threading.Thread`/`asyncio.to_thread` wiring in each endpoint | FastAPI's automatic threadpool for sync `def` endpoints (already the pattern used by `predict_sms`) | Simpler, consistent with existing codebase conventions, avoids subtle event-loop-blocking bugs |

**Key insight:** The genuinely novel engineering surface in this phase is small (perceptual hashing + a handful of layout/color heuristics + backend abstraction for OCR); the temptation to over-build (custom OCR, custom job queue, custom NLP-for-images) should be resisted in favor of composing existing, well-tested libraries and the project's own Phase 6 text pipeline.

## Common Pitfalls

### Pitfall 1: Forcing torch install onto the entire test suite
**What goes wrong:** `pytest` collection fails or slows drastically (torch import ~1-2s, plus a multi-hundred-MB install requirement) if `easyocr`/`torch` are imported at module top level anywhere reachable from `tests/`.
**Why it happens:** Natural instinct is to `import easyocr` at the top of `image_features.py`, mirroring how `spacy` is imported at the top of `text_features.py`. But spaCy's model (`en_core_web_sm`, ~15MB) is a much lighter dependency already accepted project-wide; torch is qualitatively heavier.
**How to avoid:** Lazy import inside `EasyOCRBackend.__init__`/`_get_reader`, as shown in Pattern 1. Unit tests for `image_features.py` inject `NullOCRBackend` or a fake backend returning canned text — never require torch to be installed to run `pytest tests/features/test_image_features.py`.
**Warning signs:** `ModuleNotFoundError: easyocr` appearing in CI/test runs that shouldn't need it; `pytest --collect-only` taking noticeably longer after this phase's changes.

### Pitfall 2: <500ms requirement silently violated for the image endpoint
**What goes wrong:** The project-wide comment "CRITICAL: Model is loaded ONCE at startup... sub-500ms response times" (from `main.py`) gets implicitly assumed to apply to `/predict/image` too, but EasyOCR inference on a warm CPU reader is still commonly 200ms-3s+ depending on image size/text density (CITED: general EasyOCR community reports; not independently benchmarked in this session, flag as MEDIUM confidence and something the plan should measure empirically once implemented).
**Why it happens:** Phase 6 satisfied <500ms for email/SMS because feature extraction + sklearn inference is fast (spaCy + ensemble predict is low-single-digit ms once warm); OCR's detection+recognition neural inference is a fundamentally different cost profile.
**How to avoid:** Explicitly scope this in the plan: either (a) document `/predict/image` as an intentional, justified exception to the <500ms budget (measure and report actual p50/p95 in the thesis evaluation, consistent with academic rigor expectations), or (b) implement true async processing (return a job ID immediately, client polls a `/predict/image/{job_id}` status endpoint) if the planner decides the <500ms contract must hold for the initial response. Given no existing job-queue infra, recommend (a) for Phase 7 and flag (b) as an option in Open Questions for the planner/user to decide explicitly (this is a locked-decision-shaped question, ideally resolved via `/gsd:discuss-phase`).
**Warning signs:** Load testing or even manual `curl -w "%{time_total}"` against `/predict/image` showing multi-hundred-ms to multi-second latency.

### Pitfall 3: EasyOCR's first-ever run downloads model files over the network
**What goes wrong:** `easyocr.Reader(['en'])`'s first construction anywhere (dev machine, CI, grading machine) triggers a network download of detection+recognition model weights (~64MB+) to `~/.EasyOCR/model/`. In an offline/sandboxed/CI environment without network access, this raises an exception rather than working.
**Why it happens:** EasyOCR ships model *code* via pip but not model *weights* — weights come from a separate download step at runtime (CITED: JaidedAI/EasyOCR README, GitHub).
**How to avoid:** Document this as an explicit setup step (e.g., a `scripts/download_ocr_models.py` or note in README, run once in a networked environment before first use/before grading); ensure the app doesn't crash the whole process if this download fails at lifespan startup — catch the exception and fall back to `NullOCRBackend` with a logged error, so the rest of the API stays functional.
**Warning signs:** `main.py` lifespan hanging or raising on startup in a network-restricted environment.

### Pitfall 4: Uploaded "image" isn't actually a valid image (or is a decompression bomb)
**What goes wrong:** A malformed or maliciously crafted file (wrong extension, corrupt data, or an extremely large pixel dimension "zip bomb"-style image) causes a crash or resource exhaustion when handed to Pillow/OpenCV/EasyOCR.
**Why it happens:** No systematic input validation before decoding, unlike text inputs which have simple length/format checks.
**How to avoid:** Mirror the existing `.eml` upload pattern (`file.filename.endswith(...)` check + `len(contents) > 5MB` check in `predict_email_file`) and add: `PIL.Image.open(io.BytesIO(contents)).verify()` for format validation, `Image.MAX_IMAGE_PIXELS` guard (Pillow's own decompression-bomb protection, enabled by default — do not disable it), and a reasonable max file size (e.g., 5-10MB, consistent with the email attachment limit already in the codebase).
**Warning signs:** Unhandled `PIL.Image.DecompressionBombError` or generic 500 errors on adversarial test images.

### Pitfall 5: Perceptual-hash threshold treated as a hard-coded magic number without justification
**What goes wrong:** Picking a Hamming-distance cutoff (e.g., "≤10 = brand match") without any empirical basis weakens the academic evaluation — a thesis reviewer will ask "why 10 and not 8 or 15?"
**Why it happens:** Most `imagehash` tutorials use small illustrative thresholds without rigorous derivation.
**How to avoid:** Treat the threshold as a tunable parameter (constant in code, documented), and in the Phase 7 verification/evaluation step, empirically test it against the phishing-image dataset the plan will need to source (see Open Questions on dataset availability) rather than asserting it as fact. This is consistent with the project's academic-rigor constraint (PROJECT.md: "wymaga pełnej dokumentacji teoretycznej").
**Warning signs:** Threshold value appears in code with no comment/citation/evaluation backing it.

### Pitfall 6: Feature-vector length mismatch breaking the ensemble model (same class of bug as Phase 6 Pitfall 1)
**What goes wrong:** If `image_features.py`'s output dict key set/order isn't stable and identical between training-data feature extraction and live-request feature extraction, `np.array([list(features.values())])` (the pattern used throughout `endpoints.py`) will silently produce a mis-ordered or wrong-length feature vector, since plain Python dicts preserve insertion order but any conditional key omission breaks the contract.
**Why it happens:** OCR text can be empty (image with no text) — if the code conditionally skips text features when `ocr_text == ""` instead of extracting features from the empty string (which `TextFeatureExtractor.extract_all_features("")` already handles gracefully per its own module, confirmed by its docstring pattern), key count varies between images.
**How to avoid:** Always call `extract_all_features(ocr_text)` unconditionally (even on `""`), exactly as `extract_email_features` already does for the `raw_email` falsy case (see `extractors.py`'s explicit `if not raw_email:` branch that still calls `text_extractor.extract_all_features("")`). Add a unit test asserting `len(extract_image_features(...))` is constant across an image-with-text and an image-without-text fixture.
**Warning signs:** `ValueError: X has N features, but ... is expecting M features` at prediction time — the exact failure mode already documented as Phase 6's Pitfall 1.

## Code Examples

### Layout/Color Heuristics with OpenCV (illustrative — new code, not from an external source)
```python
# src/features/image_features.py — visual heuristics section
import cv2
import numpy as np
from PIL import Image

def _extract_layout_color_features(image: Image.Image) -> dict:
    """Interpretable heuristics for 'suspicious UI element' signal (INPUT-07).
    Not ML-based — simple, explainable metrics consistent with the project's
    interpretability requirement (PROJECT.md).
    """
    arr = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # Edge density: form-heavy / button-heavy UIs (login pages) tend to have
    # more rectangular structure than plain content screenshots.
    edges = cv2.Canny(gray, 100, 200)
    edge_density = float(np.count_nonzero(edges)) / edges.size

    # Dominant color concentration: phishing login clones often reuse a
    # narrow brand palette (e.g., PayPal blue) — high concentration in a
    # few color bins can be a (weak, heuristic) signal.
    hist = cv2.calcHist([arr], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3)
    hist_normalized = hist.flatten() / hist.sum()
    color_concentration = float(np.max(hist_normalized))

    # Rectangular-contour count as a rough proxy for form fields/buttons.
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    rect_like = sum(
        1 for c in contours
        if len(cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)) == 4
    )

    return {
        "visual_edge_density": edge_density,
        "visual_color_concentration": color_concentration,
        "visual_rect_element_count": float(rect_like),
    }
```

### FastAPI Image Upload Endpoint (mirrors `predict_email_file`)
```python
# Source: pattern from src/api/endpoints.py predict_email_file (existing code, Phase 6)
@router.post("/predict/image", response_model=EmailSMSResponse, tags=["prediction"])
async def predict_image(
    file: Annotated[UploadFile, File(description="Image file (PNG/JPG)")]
):
    start_time = time.time()

    allowed_ext = (".png", ".jpg", ".jpeg")
    if file.filename and not file.filename.lower().endswith(allowed_ext):
        raise HTTPException(status_code=400, detail="File must be PNG or JPG")

    contents = await file.read()
    if len(contents) > 8 * 1024 * 1024:  # 8MB — screenshots can be larger than .eml
        raise HTTPException(status_code=400, detail="File too large (max 8MB)")

    if "ocr_backend" not in ml_models:
        raise HTTPException(status_code=503, detail="OCR backend not initialized")

    try:
        features = extract_image_features(contents, ocr_backend=ml_models["ocr_backend"])
        # ... predict_proba on image_ensemble, build EmailSMSResponse(content_type="image", ...)
        # identical pattern to predict_email_file from here on
    except ValueError as e:  # invalid image data
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Traditional OCR (Tesseract, template-matching-based) | Deep-learning OCR (EasyOCR's CRAFT + CRNN, or cloud Vision APIs) | EasyOCR public since ~2020, now the de facto easy-install Python option | Better accuracy on stylized/screenshot text (varied fonts, low contrast) typical of phishing images, at the cost of a much heavier dependency footprint |
| Pixel-diff / cryptographic hash for image comparison | Perceptual hashing (phash/dhash) or learned embeddings | Perceptual hashing has been standard for ~15 years; CNN-embedding similarity (e.g., CLIP-based) is the 2023+ research trend for phishing-clone detection (per PhishSnap, arXiv:2512.02243, LOW-MEDIUM confidence — single recent paper, dated 2025/2026) | Perceptual hashing remains the pragmatic, interpretable, low-dependency choice; CNN embeddings are the "next step" academic framing for future work |

**Deprecated/outdated:** None directly applicable — this is greenfield functionality for the project; no prior image-handling code exists to deprecate.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | EasyOCR CPU-mode per-image inference commonly falls in the 200ms-3s range (not independently benchmarked in this session — no easyocr/torch import succeeded in the sandboxed test environment during research) | Common Pitfalls #2 | If actual latency is much higher (e.g., on very large screenshots) or much lower, the <500ms-exception framing and any timeout/UX decisions in the plan may need adjustment. Planner should have an early task to empirically measure this on a representative sample. |
| A2 | A Hamming distance ≤10 on a 64-bit phash is a reasonable brand-match threshold starting point | Pattern 3, Pitfall 5 | If wrong, brand-similarity feature could be too noisy (false positives) or too strict (misses real clones) until empirically tuned — mitigated by treating it as a documented, tunable constant validated during evaluation, not a hard-coded assumption. |
| A3 | No existing task-queue/background-job infrastructure exists in the codebase (verified by absence of celery/rq/redis in requirements.txt and no `background_tasks` usage found in endpoints.py) — therefore synchronous-with-warm-model is the right MVP approach rather than building new async infra | Architecture Patterns, User Constraints (discretion) | If the user/planner actually wants true async job processing for image analysis (e.g., anticipating Phase 8's web UI needs), this recommendation under-scopes the work — should be explicitly confirmed via `/gsd:discuss-phase` before locking. |
| A4 | No dataset of phishing screenshots / brand reference images currently exists in the project's `data/` pipeline (Phase 1 downloaders target PhishTank/UCI, both URL/text-oriented, not image-oriented) | Open Questions | If a suitable image dataset must be sourced/labeled from scratch, this is a non-trivial addition to phase scope (data acquisition, not just feature engineering) and should be flagged to the planner as its own task/plan, not assumed to be a quick lookup. |

## Open Questions

1. **Should `/predict/image` be a documented exception to the <500ms budget, or should true async job processing be built?**
   - What we know: No existing async-job infrastructure; Phase 6 achieved <500ms via startup-time model loading, which OCR only partially benefits from (reader load, not per-image inference).
   - What's unclear: Whether the <500ms requirement (echoed in `main.py` comments) is a hard project-wide contract that must hold for every endpoint, or a Phase 2-era guideline specific to the URL-only MVP.
   - Recommendation: Resolve via `/gsd:discuss-phase` before planning locks in the endpoint contract — this materially changes task scope (simple synchronous handler vs. job-queue + polling endpoint + status model).

2. **Where does the reference brand-logo/screenshot dataset for perceptual-hash comparison and for training the image ensemble model come from?**
   - What we know: Phase 1's downloaders (PhishTank, UCI ML Repository) are text/URL-oriented, not image-oriented. No image dataset currently exists in `data/`.
   - What's unclear: Whether a public phishing-screenshot dataset (e.g., academic datasets referenced in phishing-visual-similarity literature) should be sourced, or whether a small hand-curated set of ~10-20 brand logos/legit login screenshots is sufficient for the academic-demo scope.
   - Recommendation: Treat dataset acquisition as an explicit early task in the plan (likely its own Wave 0 step), not an assumed-available resource. Flag to the user that this may require the same kind of research/sourcing effort Phase 1 invested in for text data.

3. **Does the image ensemble model need retraining infrastructure (`scripts/train_image_models.py`, mirroring `scripts/train_email_sms_models.py`), or can image features be combined with an existing model?**
   - What we know: Phase 6 built dedicated `email_ensemble`/`sms_ensemble` models trained on that modality's feature set (see `predict_email_file`'s `ml_models["email_ensemble"]`).
   - What's unclear: Whether Phase 7 should follow the identical "new dedicated model per modality" pattern, given the added complexity of also needing labeled image data (see Q2).
   - Recommendation: Follow the established per-modality-ensemble pattern for architectural consistency (this is what the planner should default to, per "Don't Hand-Roll" and the existing `EmailSMSResponse` contract), but flag that this is gated by Q2's dataset question.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| easyocr (project `.venv`) | INPUT-06 | ✗ (not installed in `.venv`) | — | Install via requirements.txt update; verified installable (see Package Legitimacy Audit) |
| torch (project `.venv`) | easyocr transitive dep | ✗ | — | Installs automatically with easyocr; CPU-only wheel confirmed available for this platform (macOS arm64, Python 3.9 wheel observed during verification — project `.venv` interpreter version should be confirmed by planner) |
| opencv-python-headless (project `.venv`) | INPUT-07 | ✗ (not in `.venv`; present in a separate user-level Python 3.9 install used for verification only) | — | Install via requirements.txt update |
| imagehash (project `.venv`) | INPUT-07 | ✗ | — | Install via requirements.txt update |
| Pillow (project `.venv`) | INPUT-04 | ✓ | 12.1.1 | — |
| numpy (project `.venv`) | all image processing | ✓ | 2.4.2 | — |
| system `tesseract` binary (Homebrew) | pytesseract fallback only | ✓ (dev machine only, `/opt/homebrew/bin/tesseract`) | not queried | Not guaranteed on other machines — if pytesseract fallback is implemented, document as dev-only/optional, do not depend on it for grading-machine correctness |
| Network access (for EasyOCR model weight download) | INPUT-06, first run | assumed ✓ in dev, unconfirmed for grading environment | — | Must document a pre-download step (see Pitfall 3); no offline fallback other than `NullOCRBackend` degradation |

**Missing dependencies with no fallback:**
- None — every missing dependency (easyocr, torch, opencv-python-headless, imagehash) has a clear, verified `pip install` path (all confirmed on PyPI, all passed slopcheck).

**Missing dependencies with fallback:**
- system `tesseract` binary — only needed if the pytesseract fallback path is actually implemented; core requirement (EasyOCR) does not need it.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 (confirmed via `.venv/bin/python -m pytest --collect-only -q` → 389 tests collected) |
| Config file | none detected (no `pytest.ini`/`pyproject.toml`/`setup.cfg` with pytest config found in repo root) — tests are discovered by pytest's default `test_*.py` convention under `tests/` |
| Quick run command | `.venv/bin/python -m pytest tests/features/test_image_features.py -x` |
| Full suite command | `.venv/bin/python -m pytest` (run with the project's `.venv` interpreter — running with a bare `python3 -m pytest` fails with 20 collection errors due to missing project-scoped packages, confirmed during this research) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INPUT-04 | Accepts PNG/JPG upload, rejects invalid files/oversized files | unit + API | `pytest tests/test_api.py -k image -x` (or new `tests/test_api_image.py`) | ❌ Wave 0 |
| INPUT-06 | Extracts text from image via OCR (using injected fake/Null backend for unit speed; a separate, explicitly-marked slow/integration test exercises real EasyOCR) | unit (fast, mocked) + integration (slow, real backend, optional/skippable) | `pytest tests/features/test_image_features.py -x` (unit) / `pytest tests/integration/test_image_integration.py -m slow` (integration, requires easyocr installed) | ❌ Wave 0 |
| INPUT-07 | Extracts visual features (perceptual hash similarity, layout/color heuristics) | unit | `pytest tests/features/test_image_features.py -k visual -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/features/test_image_features.py -x` (fast, no torch required — uses `NullOCRBackend`/fake injected backend)
- **Per wave merge:** `.venv/bin/python -m pytest` (full suite; if easyocr not installed in CI, integration tests should `pytest.importorskip("easyocr")` to skip gracefully rather than fail)
- **Phase gate:** Full suite green (with OCR integration test either passing or cleanly skipped) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/features/test_image_features.py` — covers INPUT-06 (OCR-text-to-features path, using fake backend), INPUT-07 (perceptual hash + layout/color heuristics)
- [ ] `tests/test_api_image.py` (or additions to `tests/test_api.py`) — covers INPUT-04 (upload validation: wrong type, oversized, corrupt image → 400; happy path → 200 with `content_type="image"`)
- [ ] `tests/integration/test_image_integration.py` — end-to-end with real EasyOCR backend; must use `pytest.importorskip("easyocr")` so it degrades gracefully in environments without the heavy deps installed
- [ ] Fixture images — need a handful of small test PNGs/JPGs under `tests/fixtures/` (e.g., one with clear text, one blank, one corrupt/truncated, one resembling a login form) — none currently exist in the repo
- [ ] Framework install: `pip install easyocr imagehash opencv-python-headless pytesseract` (add to `requirements.txt` under new "# Phase 7" section) — required only for the integration test and real runtime use, not for the fast unit-test path

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Project is an open demo, no auth by design (PROJECT.md Out of Scope) |
| V3 Session Management | no | No sessions in this API |
| V4 Access Control | no | Open demo |
| V5 Input Validation | yes | File-type allowlist (`.png`/`.jpg`/`.jpeg`), size limit (8MB proposed), `PIL.Image.open(...).verify()` for structural validation, rely on Pillow's default `MAX_IMAGE_PIXELS` decompression-bomb guard — same validation posture as the existing `.eml` upload endpoint |
| V6 Cryptography | no | No cryptographic operations introduced by this phase |
| V12 File Handling | yes | Uploaded image bytes must never be written to disk under a user-controlled filename, or executed/interpreted as anything other than pixel data; process entirely in-memory via `io.BytesIO`, consistent with how `.eml` bytes are handled in `predict_email_file` (no disk write) |

### Known Threat Patterns for image-upload + OCR/CV pipelines

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Decompression bomb (tiny file, huge decoded pixel dimensions → memory/CPU exhaustion) | Denial of Service | Rely on Pillow's default `Image.MAX_IMAGE_PIXELS` limit (do not disable it); add explicit file-size cap (8MB) before decode as a first line of defense |
| Polyglot file (valid image header + embedded malicious payload) | Tampering | `Image.verify()` + only ever process via Pillow/OpenCV's decoders (never `eval`/exec any embedded metadata); do not persist raw uploaded bytes to disk |
| Resource exhaustion via unbounded OCR/CV compute on adversarial large images | Denial of Service | Same file-size cap + optionally clamp max pixel dimensions before handing to EasyOCR/OpenCV (resize down if `width*height` exceeds a threshold) |
| EXIF/metadata-based injection (crafted EXIF fields consumed downstream) | Tampering/Information Disclosure | Since the pipeline only reads pixel data (Pillow decode → numpy array) and does not parse/display EXIF, this is low-risk here — but explicitly avoid adding EXIF-parsing code without validation if a future phase needs it |

## Sources

### Primary (HIGH confidence)
- PyPI registry (`pip index versions <pkg>`, run live 2026-09-30) — confirmed current versions for easyocr (1.7.2), torch (2.8.0), imagehash (4.3.2), pytesseract (0.3.13), opencv-python-headless (installed 4.12.0.88, latest 5.0.0.93)
- slopcheck v0.6.1 (`slopcheck install easyocr opencv-python-headless imagehash pytesseract torch Pillow`) — all six packages returned [OK]
- Direct inspection of project source: `src/features/extractors.py`, `src/features/email_features.py`, `src/features/sms_features.py`, `src/features/text_features.py`, `src/api/endpoints.py`, `src/api/models.py`, `src/api/main.py`, `src/paradigms/aggregation/aggregator.py`, `src/paradigms/aggregation/weights.py`, `src/utils/cache.py`, `requirements.txt`, `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`
- `.venv/bin/python -m pytest --collect-only -q` — confirmed 389 tests collect cleanly with the project venv (vs. 20 collection errors with bare `python3`)

### Secondary (MEDIUM confidence)
- WebSearch: EasyOCR README/PyPI summaries — Reader construction is a one-time cost, `gpu=False` for CPU mode, model weights auto-download to `~/.EasyOCR/model` on first Reader construction (github.com/JaidedAI/EasyOCR)
- WebSearch: `imagehash` library usage patterns for perceptual/near-duplicate image comparison (github.com/JohannesBuchner/imagehash)
- WebSearch: PhishSnap paper (arXiv:2512.02243) as one data point on perceptual-hashing-based phishing detection achieving ~0.79 accuracy — single paper, not cross-verified against a second independent source, treated as illustrative context rather than a hard benchmark to replicate

### Tertiary (LOW confidence — marked for validation)
- EasyOCR per-image CPU inference latency estimate (200ms-3s range) — not independently benchmarked in this session (attempted local `easyocr.Reader` construction failed in the sandboxed research environment due to a Python interpreter/package-path mismatch, not a fundamental blocker, but means the timing figure is carried over from general community reports rather than measured). **The planner should schedule an early empirical measurement task** rather than trusting this number.
- Hamming-distance-≤10 brand-match threshold — a commonly-cited illustrative value in imagehash tutorials, not independently derived or benchmarked against a phishing-specific dataset in this research session.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every package version-verified against live PyPI and slopcheck-approved; EasyOCR is explicitly the requirement-named library (no ambiguity to resolve)
- Architecture: HIGH — directly derived from and consistent with the existing, working Phase 6 patterns already in the codebase (extractors.py dispatch, lifespan model loading, EmailSMSResponse contract, aggregator reuse)
- Pitfalls: MEDIUM-HIGH — the dependency-isolation and feature-vector-consistency pitfalls are HIGH confidence (directly observed in this codebase / logically certain); the exact latency figures underlying the <500ms pitfall are MEDIUM-LOW confidence (not benchmarked locally)

**Research date:** 2026-09-30
**Valid until:** 2026-10-30 (30 days — stack is fairly stable, but EasyOCR/torch release cadence and the still-open dataset/async-architecture questions mean this should be revisited if the phase start is significantly delayed)
