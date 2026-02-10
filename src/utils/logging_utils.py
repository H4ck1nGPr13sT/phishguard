"""JSON-based logging setup for pipeline execution tracking.

Provides structured logging with JSON output format for easy parsing and
analysis. Supports log rotation to prevent unbounded disk usage.
"""

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Format log records as JSON objects.

    Each log record is formatted as a JSON object with fields:
    - timestamp: ISO 8601 format
    - level: Log level name (INFO, WARNING, ERROR, etc.)
    - module: Module name where log originated
    - message: Log message
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string.

        Args:
            record: Log record to format

        Returns:
            JSON string representation of log record
        """
        log_obj = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'module': record.module,
            'message': record.getMessage(),
        }
        return json.dumps(log_obj)


def setup_logging(log_dir: Path, log_level: int = logging.INFO) -> logging.Logger:
    """Configure JSON logging with rotation.

    Creates a logger with:
    - JSON format for structured output
    - Rotating file handler (10MB per file, 5 backups)
    - Console handler for immediate feedback

    Args:
        log_dir: Directory to store log files
        log_level: Minimum log level to capture (default: INFO)

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logging(Path('./logs'))
        >>> logger.info('Pipeline started')
        >>> logger.error('Download failed', extra={'source': 'phishtank'})
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger('phishguard')
    logger.setLevel(log_level)

    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # File handler with rotation (10MB, 5 backups)
    file_handler = RotatingFileHandler(
        log_dir / 'pipeline.jsonl',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)

    # Console handler for immediate feedback (non-JSON for readability)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    return logger
