"""Unit tests for the screener's growth-rate priority (no network)."""
from scripts.fetch_sp500 import choose_growth_rate

ANALYST = {"rate": 0.18, "basis": "next_year"}


def test_finviz_wins_when_available():
    assert choose_growth_rate(0.1899, ANALYST, 0.20, 0.10) == (18.99, "finviz_5y")


def test_falls_back_in_order():
    assert choose_growth_rate(None, ANALYST, 0.20, 0.10) == (18.0, "yahoo_analyst")
    assert choose_growth_rate(None, None, 0.20, 0.10) == (20.0, "yahoo_cf_history")
    assert choose_growth_rate(None, None, None, 0.10) == (10.0, "yahoo_eps_history")
    assert choose_growth_rate(None, None, None, None) == (5.0, "default")
