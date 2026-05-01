"""Shared pytest fixtures and configuration for the detector test suite.

- Adds a `--no-network` CLI option that skips tests marked `@pytest.mark.network`.
- Same effect when the env var `PYTEST_OFFLINE=1` is set.
- Provides the `synthetic_ohlc` fixture: a callable that builds tz-naive,
  business-day-indexed OHLC frames from `(open, high, low, close)` tuples.
"""
from __future__ import annotations

import os
from typing import Callable, List, Tuple

import pandas as pd
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--no-network",
        action="store_true",
        default=False,
        help="Skip tests that require live yfinance / network access.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "network: marks tests that require live network access (yfinance fetch).",
    )


def pytest_collection_modifyitems(config, items):
    no_network = (
        config.getoption("--no-network")
        or os.environ.get("PYTEST_OFFLINE") == "1"
    )
    if not no_network:
        return
    skip_marker = pytest.mark.skip(reason="--no-network or PYTEST_OFFLINE=1 set")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip_marker)


@pytest.fixture
def synthetic_ohlc() -> Callable[[List[Tuple[float, float, float, float]], str], pd.DataFrame]:
    """Return a builder that constructs deterministic OHLC frames for unit tests.

    Each row is `(open, high, low, close)`. The index is a tz-naive DatetimeIndex
    on US business days starting at `start_date`.
    """

    def _build(
        rows: List[Tuple[float, float, float, float]],
        start_date: str = "2024-01-01",
    ) -> pd.DataFrame:
        idx = pd.bdate_range(start=start_date, periods=len(rows))
        df = pd.DataFrame(
            rows,
            columns=["Open", "High", "Low", "Close"],
            index=idx,
        )
        return df

    return _build
