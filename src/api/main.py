"""FastAPI application with lifespan events for model loading.

CRITICAL: Model is loaded ONCE at startup via lifespan events,
not per-request. This ensures sub-500ms response times.
"""

# OpenMP safety — MUST run before any import that loads an OpenMP runtime
# (xgboost via the ensembles, torch via the EasyOCR backend). On macOS both
# ship their own OpenMP; loading both in one process without these settings
# segfaults or DEADLOCKS the server during lifespan startup (the app then
# never becomes reachable). setdefault() lets an explicit env override win.
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.api.web import WEB_DIR

from src.models.predict import load_model
from src.models.ensemble import load_ensemble
from src.optimization.model_registry import get_active_model
from src.paradigms.rules import RuleEngine
from src.paradigms.bayesian import BayesianClassifier
from src.paradigms.aggregation import MultiParadigmAggregator
from src.features.ocr import resolve_ocr_backend, NullOCRBackend
import joblib

# Global model storage - loaded once at startup
ml_models = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML model at startup, clean up at shutdown.

    CRITICAL: Model loaded once here, not per-request.
    This ensures sub-500ms response times.
    """
    print("Loading ML models...")

    # Load primary model from registry (defaults to GA-optimized if available)
    try:
        ml_models["phishing_detector"] = get_active_model("rf")
        print(f"Primary model loaded from registry: {type(ml_models['phishing_detector']).__name__}")
    except FileNotFoundError:
        # Fallback to baseline if registry not configured
        print("Registry not configured, falling back to baseline model...")
        model_path = Path("models/rf_pipeline.joblib")
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                "Run training first: python -m src.models.train"
            )
        ml_models["phishing_detector"] = load_model(model_path)
        print(f"Primary model loaded (baseline): {type(ml_models['phishing_detector']).__name__}")

    # Load active ensemble from registry
    ensemble_loaded = 0
    try:
        ml_models["ensemble"] = get_active_model("ensemble")
        ml_models["voting_soft"] = ml_models["ensemble"]  # Alias for endpoint compatibility
        ensemble_loaded += 1
        print(f"Active ensemble loaded from registry (weighted voting)")
    except FileNotFoundError:
        print("Active ensemble not found in registry, trying fallback...")

        # Fallback to loading ensembles directly
        ensemble_dir = Path("models/ensemble")
        if ensemble_dir.exists():
            # Load soft voting ensemble
            soft_path = ensemble_dir / "voting_soft.joblib"
            if soft_path.exists():
                try:
                    ml_models["voting_soft"] = load_ensemble(soft_path)
                    ensemble_loaded += 1
                    print(f"Loaded voting_soft ensemble (fallback)")
                except Exception as e:
                    print(f"Warning: Failed to load voting_soft: {e}")

            # Load hard voting ensemble
            hard_path = ensemble_dir / "voting_hard.joblib"
            if hard_path.exists():
                try:
                    ml_models["voting_hard"] = load_ensemble(hard_path)
                    ensemble_loaded += 1
                    print(f"Loaded voting_hard ensemble (fallback)")
                except Exception as e:
                    print(f"Warning: Failed to load voting_hard: {e}")

            # Load stacking ensemble (optional)
            stacking_path = ensemble_dir / "stacking.joblib"
            if stacking_path.exists():
                try:
                    ml_models["stacking"] = load_ensemble(stacking_path)
                    ensemble_loaded += 1
                    print(f"Loaded stacking ensemble (fallback)")
                except Exception as e:
                    print(f"Warning: Failed to load stacking: {e}")
        else:
            print(f"Warning: Ensemble directory not found at {ensemble_dir}")

    # Load Phase 5 paradigm components
    print("Loading Phase 5 paradigm components...")

    # Load rule engine
    try:
        ml_models["rule_engine"] = RuleEngine()
        print(f"Rule engine loaded: {len(ml_models['rule_engine'].ruleset.rules)} rules")
    except Exception as e:
        print(f"Warning: Failed to load rule engine: {e}")

    # Load Bayesian classifier
    bayesian_path = Path("models/bayesian/bayesian_classifier.joblib")
    if bayesian_path.exists():
        try:
            ml_models["bayesian"] = BayesianClassifier.load(bayesian_path)
            print("Bayesian classifier loaded")
        except Exception as e:
            print(f"Warning: Failed to load Bayesian classifier: {e}")
    else:
        print(f"Warning: Bayesian model not found at {bayesian_path}")

    # Initialize aggregator
    ml_models["aggregator"] = MultiParadigmAggregator()
    print("Multi-paradigm aggregator initialized")

    # Load email/SMS models (Phase 6)
    email_sms_dir = Path("models/email_sms")
    email_sms_loaded = 0
    if email_sms_dir.exists():
        # Load email ensemble
        email_ensemble_path = email_sms_dir / "ensemble_email.joblib"
        if email_ensemble_path.exists():
            try:
                email_model_data = joblib.load(email_ensemble_path)
                ml_models["email_ensemble"] = email_model_data["model"]
                ml_models["email_feature_names"] = email_model_data["feature_names"]
                ml_models["email_feature_count"] = email_model_data["feature_count"]
                email_sms_loaded += 1
                print(f"Email ensemble loaded ({email_model_data['feature_count']} features, {email_model_data['test_accuracy']:.4f} accuracy)")
            except Exception as e:
                print(f"Warning: Failed to load email ensemble: {e}")

        # Load SMS ensemble
        sms_ensemble_path = email_sms_dir / "ensemble_sms.joblib"
        if sms_ensemble_path.exists():
            try:
                sms_model_data = joblib.load(sms_ensemble_path)
                ml_models["sms_ensemble"] = sms_model_data["model"]
                ml_models["sms_feature_names"] = sms_model_data["feature_names"]
                ml_models["sms_feature_count"] = sms_model_data["feature_count"]
                email_sms_loaded += 1
                print(f"SMS ensemble loaded ({sms_model_data['feature_count']} features, {sms_model_data['test_accuracy']:.4f} accuracy)")
            except Exception as e:
                print(f"Warning: Failed to load SMS ensemble: {e}")
    else:
        print(f"Warning: Email/SMS models not found. Run scripts/train_email_sms_models.py")

    # Load and warm the OCR backend (Phase 7). Warming here (not per-request)
    # is required to keep /predict/image within the documented latency
    # exception — EasyOCR's first-use model load costs several seconds.
    # ANY failure here (offline env, model-download failure) must NOT crash
    # startup: fall back to NullOCRBackend so the rest of the API stays
    # functional (T-07-12).
    try:
        ml_models["ocr_backend"] = resolve_ocr_backend()
        if hasattr(ml_models["ocr_backend"], "warm_up"):
            ml_models["ocr_backend"].warm_up()
        print(f"OCR backend loaded and warmed: {type(ml_models['ocr_backend']).__name__}")
    except Exception as e:
        print(f"Warning: Failed to warm OCR backend, falling back to NullOCRBackend: {e}")
        ml_models["ocr_backend"] = NullOCRBackend()

    total_models = len(ml_models)
    print(f"Total models loaded: {total_models} (1 primary + {ensemble_loaded} ensemble + Phase 5 paradigms + {email_sms_loaded} email/SMS)")

    yield  # Application runs here

    print("Shutting down, clearing models...")
    ml_models.clear()


app = FastAPI(
    title="PhishGuard API",
    description="REST API for URL phishing detection using multi-paradigm analysis. "
                "Combines ML ensemble (7 classifiers), rule-based expert system, "
                "and Bayesian probabilistic classifier. "
                "Provides single predictions (/predict), ensemble predictions "
                "(/predict/ensemble), and multi-paradigm predictions (/predict/multi-paradigm).",
    version="4.0.0",  # Updated version for Phase 7 image/OCR support
    lifespan=lifespan,
)

# Static assets (CSS/JS) for the web UI, mounted at an absolute,
# CWD-independent path (Phase 8).
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

# Paths that need inline scripts / CDN assets (Swagger UI, ReDoc, the raw
# OpenAPI schema) and must NOT receive the CSP header, or they break.
_CSP_EXEMPT_PREFIXES = ("/docs", "/redoc")
_CSP_EXEMPT_EXACT = {"/openapi.json"}


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    """Set security headers (T-08-01/02/03) on every response.

    nosniff and X-Frame-Options DENY apply everywhere. The CSP
    (default-src 'self') is scoped to skip Swagger/ReDoc/OpenAPI paths,
    which rely on inline scripts and CDN assets (T-08-05).
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"

    path = request.url.path
    if not (path.startswith(_CSP_EXEMPT_PREFIXES) or path in _CSP_EXEMPT_EXACT):
        response.headers["Content-Security-Policy"] = "default-src 'self'"

    return response

# Import and include endpoints
from src.api.endpoints import router
from src.api.web import web_router
from src.api.batch import router as batch_router

app.include_router(web_router)
app.include_router(router)
app.include_router(batch_router)
