#!/usr/bin/env python3
"""
Centralized path configuration for Writing Style Clone.

Resolves data directory from:
1. WRITING_STYLE_DATA environment variable (if set)
2. Default: ~/Documents/my-writing-style

Usage:
    from config import get_data_dir, get_path

    DATA_DIR = get_data_dir()
    RAW_DIR = get_path('raw_samples')
"""

import os
from pathlib import Path
from functools import lru_cache

DEFAULT_DATA_DIR = Path.home() / "Documents" / "my-writing-style"
ENV_VAR = "WRITING_STYLE_DATA"


@lru_cache(maxsize=1)
def get_data_dir() -> Path:
    """
    Resolve data directory from env var or default.

    Returns:
        Path: Resolved and expanded data directory path
    """
    env_path = os.environ.get(ENV_VAR)
    if env_path:
        return Path(env_path).expanduser().resolve()
    return DEFAULT_DATA_DIR.expanduser().resolve()


def get_path(*subdirs: str) -> Path:
    """
    Get path relative to data directory.

    Args:
        *subdirs: Subdirectory path components

    Returns:
        Path: Full path within data directory

    Example:
        get_path('raw_samples')  # Returns DATA_DIR / 'raw_samples'
        get_path('clusters', 'email_clusters.json')
    """
    return get_data_dir() / Path(*subdirs)
