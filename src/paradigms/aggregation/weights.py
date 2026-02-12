"""Paradigm weight management for multi-paradigm aggregation.

Default weights: ML ensemble (0.5), Rules (0.3), Bayesian (0.2)
based on Phase 5 research recommendations.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ParadigmWeights:
    """Configurable weights for paradigm aggregation.

    Weights must sum to 1.0 and stay within bounds:
    - ML ensemble: 0.4-0.6 (dominant but not overwhelming)
    - Rules: 0.2-0.4 (interpretable contribution)
    - Bayesian: 0.1-0.3 (probabilistic complement)

    Attributes:
        ml_ensemble: Weight for ML ensemble prediction
        rules: Weight for rule-based system score
        bayesian: Weight for Bayesian posterior
    """

    ml_ensemble: float = 0.5
    rules: float = 0.3
    bayesian: float = 0.2

    def __post_init__(self):
        """Validate weights after initialization."""
        self._validate()

    def _validate(self):
        """Ensure weights sum to 1.0 and are in valid ranges."""
        total = self.ml_ensemble + self.rules + self.bayesian
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Weights must sum to 1.0, got {total:.4f}. "
                f"ML={self.ml_ensemble}, Rules={self.rules}, Bayesian={self.bayesian}"
            )

        # Bound validation (soft warning, not error)
        if not (0.4 <= self.ml_ensemble <= 0.6):
            import warnings
            warnings.warn(
                f"ML ensemble weight {self.ml_ensemble} outside recommended range [0.4, 0.6]"
            )
        if not (0.2 <= self.rules <= 0.4):
            import warnings
            warnings.warn(
                f"Rules weight {self.rules} outside recommended range [0.2, 0.4]"
            )
        if not (0.1 <= self.bayesian <= 0.3):
            import warnings
            warnings.warn(
                f"Bayesian weight {self.bayesian} outside recommended range [0.1, 0.3]"
            )

    def to_dict(self) -> Dict[str, float]:
        """Return weights as dictionary."""
        return {
            'ml_ensemble': self.ml_ensemble,
            'rules': self.rules,
            'bayesian': self.bayesian
        }

    @classmethod
    def from_dict(cls, d: Dict[str, float]) -> 'ParadigmWeights':
        """Create from dictionary."""
        return cls(
            ml_ensemble=d.get('ml_ensemble', 0.5),
            rules=d.get('rules', 0.3),
            bayesian=d.get('bayesian', 0.2)
        )


# Default weights based on research
DEFAULT_WEIGHTS = ParadigmWeights(ml_ensemble=0.5, rules=0.3, bayesian=0.2)
