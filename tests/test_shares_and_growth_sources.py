"""Unit tests for share-count, price and analyst-growth lookups (no network)."""
import pandas as pd

from shared.fetchers import YahooFinanceFetcher


class _FakeTicker:
    def __init__(self, fast_info=None, growth_estimates=None):
        self.fast_info = fast_info or {}
        self.growth_estimates = growth_estimates


def _fetcher(info=None, **ticker_kwargs):
    f = YahooFinanceFetcher.__new__(YahooFinanceFetcher)
    f.symbol = "TEST"
    f.info = info
    f.ticker = _FakeTicker(**ticker_kwargs)
    return f


def _estimates(**rows):
    return pd.DataFrame({"stockTrend": rows, "indexTrend": {k: 0.1 for k in rows}})


def test_shares_prefer_all_class_count():
    # Alphabet-style: sharesOutstanding is one class, implied covers all classes
    f = _fetcher({"sharesOutstanding": 5_888e6, "impliedSharesOutstanding": 12_294e6})
    assert f.get_total_shares_outstanding() == 12_294e6


def test_shares_fall_back_to_single_class_then_fast_info():
    assert _fetcher({"sharesOutstanding": 100e6}).get_total_shares_outstanding() == 100e6
    assert _fetcher({}, fast_info={"shares": 250e6}).get_total_shares_outstanding() == 250e6
    assert _fetcher(None).get_total_shares_outstanding() is None


def test_price_falls_back_to_fast_info():
    assert _fetcher({"currentPrice": 10.0}).get_last_price() == 10.0
    assert _fetcher({"previousClose": 9.0}).get_last_price() == 9.0
    assert _fetcher({}, fast_info={"last_price": 8.0}).get_last_price() == 8.0
    assert _fetcher({}).get_last_price() is None


def test_analyst_growth_prefers_long_term():
    f = _fetcher({}, growth_estimates=_estimates(**{"+1y": 0.18, "LTG": 0.12}))
    assert f.get_analyst_growth_estimate() == {"rate": 0.12, "basis": "long_term"}


def test_analyst_growth_uses_next_year_when_long_term_blank():
    f = _fetcher({}, growth_estimates=_estimates(**{"+1y": 0.18, "LTG": float("nan")}))
    assert f.get_analyst_growth_estimate() == {"rate": 0.18, "basis": "next_year"}


def test_analyst_growth_none_when_missing_or_negative():
    assert _fetcher({}, growth_estimates=None).get_analyst_growth_estimate() is None
    f = _fetcher({}, growth_estimates=_estimates(**{"+1y": -0.05, "LTG": float("nan")}))
    assert f.get_analyst_growth_estimate() is None
