"""FastAPI application with lifespan events for model loading.

CRITICAL: Model is loaded ONCE at startup via lifespan events,
not per-request. This ensures sub-500ms response times.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathlib import Path

from src.models.predict import load_model
from src.models.ensemble import load_ensemble
from src.optimization.model_registry import get_active_model
from src.paradigms.rules import RuleEngine
from src.paradigms.bayesian import BayesianClassifier
from src.paradigms.aggregation import MultiParadigmAggregator

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

    total_models = len(ml_models)
    print(f"Total models loaded: {total_models} (1 primary + {ensemble_loaded} ensemble + Phase 5 paradigms)")

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
    version="2.0.0",  # Updated version for Phase 5
    lifespan=lifespan,
)

# Import and include endpoints
from src.api.endpoints import router

app.include_router(router)
