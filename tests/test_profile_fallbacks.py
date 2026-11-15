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


def _timeseries_response(code):
    response = MagicMock()
    response.json.return_value = {"timeseries": {"result": [
        {"meta": {"symbol": ["TSM"]}, "timestamp": [1],
         "annualOperatingCashFlow": [None, {"asOfDate": "2025-12-31", "currencyCode": code}]},
    ]}}
    return response


def test_reporting_currency_read_from_statements_when_profile_withheld():
    fetcher = _fetcher({}, metadata={"longName": "TSMC", "exchangeName": "NYQ", "currency": "USD"})
    fetcher.ticker._data.get.return_value = _timeseries_response("TWD")
    with patch("shared.fetchers.yahoo_finance.yf.Search") as search:
        search.return_value.quotes = []
        profile = fetcher.get_profile()
    assert profile["financial_currency"] == "TWD"
    assert profile["trading_currency"] == "USD"


def test_exchange_rate_same_currency_needs_no_lookup():
    with patch("shared.fetchers.yahoo_finance.yf.Ticker") as ticker_cls:
        assert YahooFinanceFetcher.get_exchange_rate("USD", "USD") == 1.0
    ticker_cls.assert_not_called()


def test_exchange_rate_looks_up_currency_pair():
    with patch("shared.fetchers.yahoo_finance.yf.Ticker") as ticker_cls:
        ticker_cls.return_value.fast_info = {"last_price": 0.0304}
        assert YahooFinanceFetcher.get_exchange_rate("TWD", "USD") == 0.0304
    ticker_cls.assert_called_once_with("TWDUSD=X")


def test_exchange_rate_none_when_lookup_fails_or_currency_unknown():
    with patch("shared.fetchers.yahoo_finance.yf.Ticker", side_effect=RuntimeError("429")):
        assert YahooFinanceFetcher.get_exchange_rate("TWD", "USD") is None
    assert YahooFinanceFetcher.get_exchange_rate(None, "USD") is None


def _quarterly(rows):
    cols = pd.to_datetime(["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30"])
    return pd.DataFrame(rows, index=cols).T


def test_free_cash_flow_is_trailing_twelve_months():
    fetcher = _fetcher({})
    fetcher.cash_flow = pd.DataFrame({pd.Timestamp("2025-12-31"): {"Free Cash Flow": 999.0}})
    fetcher.quarterly_cashflow = _quarterly({"Free Cash Flow": [10.0, 20.0, 30.0, 40.0, 500.0]})
    assert fetcher.get_free_cash_flow_with_basis() == (100.0, "ttm")
    assert fetcher.get_free_cash_flow() == 100.0


def test_free_cash_flow_ttm_from_ocf_minus_capex():
    fetcher = _fetcher({})
    fetcher.cash_flow = pd.DataFrame({pd.Timestamp("2025-12-31"): {"Free Cash Flow": 999.0}})
    fetcher.quarterly_cashflow = _quarterly({
        "Operating Cash Flow": [50.0, 50.0, 50.0, 50.0, 1.0],
        "Capital Expenditure": [-10.0, -10.0, -10.0, -10.0, -1.0],
    })
    assert fetcher.get_free_cash_flow_with_basis() == (160.0, "ttm")


def test_free_cash_flow_falls_back_to_fiscal_year_for_half_yearly_filers():
    fetcher = _fetcher({})
    fetcher.cash_flow = pd.DataFrame({pd.Timestamp("2025-12-31"): {"Free Cash Flow": 999.0}})
    fetcher.quarterly_cashflow = _quarterly({"Free Cash Flow": [10.0, np.nan, 30.0, np.nan, np.nan]})
    assert fetcher.get_free_cash_flow_with_basis() == (999.0, "annual")
