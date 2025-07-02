"""
Logging configuration for TikTok Shop Creator CRM
Provides structured logging with proper formatting and levels
"""

import logging
import sys
from typing import Optional
from functools import lru_cache


@lru_cache()
def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger instance with consistent configuration.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if handlers haven't been added
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger