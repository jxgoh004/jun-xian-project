"""Fallbacks used when Yahoo withholds the company profile (`info`).

Yahoo rate-limits that endpoint on shared cloud hosts, so the fetcher must get
name, exchange, sector and beta from other endpoints — and must not pretend to
know the reporting currency.
"""
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from shared.fetchers.yahoo_finance import YahooFinanceFetcher


def _fetcher(info, metadata=None):
    with patch("shared.fetchers.yahoo_finance.yf.Ticker") as ticker_cls:
        fetcher = YahooFinanceFetcher("TSM")
    fetcher.ticker = MagicMock()
    fetcher.ticker.history_metadata = metadata or {}
    fetcher.info = info
    return fetcher


def _monthly(returns):
    index = pd.date_range("2021-01-31", periods=len(returns) + 1, freq="ME", tz="America/New_York")
    return pd.Series(100 * np.cumprod(np.concatenate([[1.0], 1 + np.asarray(returns)])), index=index)


def test_profile_prefers_yahoo_info():
    fetcher = _fetcher({
        "longName": "Taiwan Semiconductor", "sector": "Technology", "industry": "Semiconductors",
        "exchange": "NYQ", "currency": "USD", "financialCurrency": "TWD",
    })
    with patch("shared.fetchers.yahoo_finance.yf.Search") as search:
        profile = fetcher.get_profile()
    search.assert_not_called()
    assert profile["financial_currency"] == "TWD"
    assert profile["trading_currency"] == "USD"
    assert profile["name"] == "Taiwan Semiconductor"


def test_profile_falls_back_to_chart_metadata_and_search():
    fetcher = _fetcher({}, metadata={"longName": "Taiwan Semiconductor", "exchangeName": "NYQ", "currency": "USD"})
    with patch("shared.fetchers.yahoo_finance.yf.Search") as search:
        search.return_value.quotes = [
            {"symbol": "TSMC34.SA", "sector": "Wrong"},
            {"symbol": "TSM", "sector": "Technology", "industry": "Semiconductors"},
        ]
        profile = fetcher.get_profile()
    assert profile["name"] == "Taiwan Semiconductor"
    assert profile["exchange"] == "NYQ"
    assert profile["sector"] == "Technology"
    assert profile["industry"] == "Semiconductors"
    assert profile["trading_currency"] == "USD"
    # The trading currency must never be passed off as the reporting currency
    assert profile["financial_currency"] is None


def test_profile_survives_every_fallback_failing():
    fetcher = _fetcher({})
    type(fetcher.ticker).history_metadata = property(lambda self: (_ for _ in ()).throw(RuntimeError("429")))
    with patch("shared.fetchers.yahoo_finance.yf.Search", side_effect=RuntimeError("429")):
        profile = fetcher.get_profile()
    assert profile == {"name": None, "sector": None, "industry": None, "exchange": None,
                       "trading_currency": None, "financial_currency": None}


def test_beta_uses_published_value_when_available():
    assert _fetcher({"beta": 1.23}).get_beta() == {"beta": 1.23, "source": "yahoo"}


def test_beta_computed_from_monthly_returns():
    rng = np.random.default_rng(0)
    index_returns = rng.normal(0.01, 0.04, 60)
    stock_returns = 1.5 * index_returns          # exactly 1.5x the index
    result = YahooFinanceFetcher._beta_from_prices(_monthly(stock_returns), _monthly(index_returns))
    assert result == {"beta": 1.5, "source": "computed"}


def test_beta_needs_two_years_of_history():
    returns = np.full(12, 0.01)
    assert YahooFinanceFetcher._beta_from_prices(_monthly(returns), _monthly(returns)) is None


def test_beta_none_when_price_history_fails():
    fetcher = _fetcher({})
    fetcher.ticker.history.side_effect = RuntimeError("429")
    assert fetcher.get_beta() is None
