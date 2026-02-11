"""MLflow tracking utilities for genetic algorithm optimization.

This module provides helper functions to track GA optimization experiments
using MLflow. It enables:

- Experiment setup with consistent naming
- Per-generation fitness tracking (avg, max, min, std)
- Best individual logging (hyperparameters, fitness, duration)
- Convergence analysis across generations
- Optimized model persistence with metadata

Integration pattern:
- Single MLflow run per classifier optimization
- Generation metrics logged with step parameter
- Final model and hyperparameters logged as artifacts and params
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

import joblib
import mlflow
from deap import tools

logger = logging.getLogger(__name__)


def setup_experiment(experiment_name: str = "phase_4_ga_optimization") -> str:
    """Setup MLflow experiment for GA optimization tracking.

    Creates or retrieves MLflow experiment by name. Experiments group
    related runs (e.g., all classifier optimizations for Phase 4).

    Args:
        experiment_name: Name of MLflow experiment (default: phase_4_ga_optimization)

    Returns:
        Experiment ID string for reference in runs

    Example:
        >>> exp_id = setup_experiment("my_ga_experiment")
        >>> print(f"Experiment ID: {exp_id}")
    """
    experiment = mlflow.get_experiment_by_name(experiment_name)

    if experiment is None:
        # Create new experiment
        experiment_id = mlflow.create_experiment(experiment_name)
        logger.info(f"Created MLflow experiment: {experiment_name} (ID: {experiment_id})")
    else:
        experiment_id = experiment.experiment_id
        logger.info(f"Using existing MLflow experiment: {experiment_name} (ID: {experiment_id})")

    mlflow.set_experiment(experiment_name)

    return experiment_id


def log_generation(gen_number: int, population: List[Any], stats: tools.Statistics) -> None:
    """Log generation statistics to MLflow.

    Tracks fitness statistics per generation to monitor convergence:
    - avg_fitness: Population average (exploration indicator)
    - max_fitness: Best individual in generation
    - min_fitness: Worst individual in generation
    - std_fitness: Fitness diversity (convergence indicator)

    Low std_fitness suggests premature convergence.

    Args:
        gen_number: Current generation number (0-indexed)
        population: DEAP population with evaluated fitness
        stats: DEAP statistics object configured with fitness metrics

    Example:
        >>> # In GA loop
        >>> for gen in range(n_generations):
        ...     # ... evolution logic ...
        ...     log_generation(gen, population, stats)
    """
    # Compile statistics for this generation
    record = stats.compile(population)

    # Log as MLflow metrics with generation as step
    mlflow.log_metrics({
        "avg_fitness": record["avg"],
        "max_fitness": record["max"],
        "min_fitness": record["min"],
        "std_fitness": record["std"]
    }, step=gen_number)

    logger.debug(
        f"Gen {gen_number}: avg={record['avg']:.4f}, "
        f"max={record['max']:.4f}, std={record['std']:.4f}"
    )


def log_best_individual(
    classifier_name: str,
    individual: List[Any],
    hyperparams: Dict[str, Any],
    fitness: float,
    duration: float,
    generations: int
) -> None:
    """Log best individual's hyperparameters and fitness to MLflow.

    Records final optimization results as MLflow parameters and metrics:
    - Hyperparameters as params (searchable in MLflow UI)
    - Final fitness as metric
    - Optimization duration and generations

    Args:
        classifier_name: Classifier name (rf, svm, mlp, etc.)
        individual: Raw DEAP individual (for reference)
        hyperparams: Decoded hyperparameter dictionary
        fitness: Best fitness value (F1-score from CV)
        duration: Optimization duration in seconds
        generations: Number of generations run

    Example:
        >>> log_best_individual(
        ...     "rf", best_ind, {"n_estimators": 200, "max_depth": 15},
        ...     fitness=0.9247, duration=1200.5, generations=30
        ... )
    """
    # Log hyperparameters as params
    for param_name, param_value in hyperparams.items():
        mlflow.log_param(param_name, param_value)

    # Log final metrics
    mlflow.log_metric("final_fitness", fitness)
    mlflow.log_metric("optimization_duration_sec", duration)

    # Log tags for filtering in MLflow UI
    mlflow.set_tags({
        "classifier_name": classifier_name,
        "model_type": "ga_optimized",
        "generations": str(generations)
    })

    logger.info(
        f"Logged best individual for {classifier_name}: "
        f"fitness={fitness:.4f}, duration={duration:.1f}s"
    )


def log_convergence_analysis(logbook: tools.Logbook) -> None:
    """Analyze and log convergence metrics from GA logbook.

    Extracts convergence patterns from fitness history:
    - generations_to_convergence: When fitness improvement plateaued
    - fitness_improvement: Total improvement from gen 0 to final
    - final_std: Final population diversity (low = converged)

    Args:
        logbook: DEAP logbook with generation records

    Example:
        >>> # After GA completes
        >>> log_convergence_analysis(logbook)
    """
    if len(logbook) == 0:
        logger.warning("Empty logbook, skipping convergence analysis")
        return

    # Extract fitness history
    initial_fitness = logbook[0]["max"]
    final_fitness = logbook[-1]["max"]
    final_std = logbook[-1]["std"]

    # Calculate improvement
    fitness_improvement = final_fitness - initial_fitness

    # Detect convergence point (when max fitness stops improving by >0.001 for 5 gens)
    generations_to_convergence = len(logbook)  # Default: never converged
    convergence_threshold = 0.001
    no_improvement_window = 5

    for i in range(no_improvement_window, len(logbook)):
        recent_max = max(logbook[j]["max"] for j in range(i - no_improvement_window, i))
        current_max = logbook[i]["max"]

        if current_max - recent_max < convergence_threshold:
            generations_to_convergence = i
            break

    # Log convergence metrics
    mlflow.log_metrics({
        "initial_fitness": initial_fitness,
        "final_fitness": final_fitness,
        "fitness_improvement": fitness_improvement,
        "generations_to_convergence": generations_to_convergence,
        "final_std": final_std
    })

    logger.info(
        f"Convergence analysis: improvement={fitness_improvement:.4f}, "
        f"converged_at=gen_{generations_to_convergence}, final_std={final_std:.4f}"
    )


def save_optimized_model(
    classifier_name: str,
    model: Any,
    hyperparams: Dict[str, Any],
    fitness: float,
    output_dir: Path
) -> Path:
    """Save optimized model with metadata to disk and log to MLflow.

    Persists model using joblib with compression. Includes metadata:
    - Hyperparameters used
    - Fitness achieved
    - Timestamp
    - Classifier name

    Args:
        classifier_name: Classifier name (rf, svm, mlp, etc.)
        model: Trained sklearn Pipeline
        hyperparams: Best hyperparameters
        fitness: Best fitness value
        output_dir: Directory for optimized models

    Returns:
        Path to saved model file

    Example:
        >>> model_path = save_optimized_model(
        ...     "rf", best_model, best_params,
        ...     fitness=0.9247, output_dir=Path("models/optimized")
        ... )
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create model metadata
    metadata = {
        "classifier_name": classifier_name,
        "hyperparameters": hyperparams,
        "fitness": fitness,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model_type": "ga_optimized"
    }

    # Wrap model with metadata
    model_artifact = {
        "model": model,
        "metadata": metadata
    }

    # Save to disk
    model_path = output_dir / f"{classifier_name}_optimized.joblib"
    joblib.dump(model_artifact, model_path, compress=3, protocol=5)

    logger.info(f"Saved optimized model to {model_path}")

    # Log as MLflow artifact
    try:
        mlflow.log_artifact(str(model_path))
        logger.info(f"Logged model artifact to MLflow: {model_path.name}")
    except Exception as e:
        logger.warning(f"Failed to log artifact to MLflow: {e}")

    # Also save metadata as JSON for easy inspection
    metadata_path = output_dir / f"{classifier_name}_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    try:
        mlflow.log_artifact(str(metadata_path))
    except Exception as e:
        logger.warning(f"Failed to log metadata artifact: {e}")

    return model_path
