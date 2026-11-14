"""Unit tests for YahooFinanceFetcher.get_normalized_free_cash_flow (no network)."""
import pandas as pd
import pytest

from shared.fetchers import YahooFinanceFetcher


def _fetcher(annual_capex, quarterly_capex, quarterly_ocf,
             annual_dates=None, quarterly_dates=None):
    """Build a fetcher with hand-made cash flow frames (newest column first)."""
    f = YahooFinanceFetcher.__new__(YahooFinanceFetcher)
    f.symbol = "TEST"
    annual_dates = annual_dates if annual_dates is not None else pd.to_datetime(
        ["2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31", "2021-12-31"][:len(annual_capex)])
    quarterly_dates = quarterly_dates if quarterly_dates is not None else pd.to_datetime(
        ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30"][:len(quarterly_capex)])
    f.cash_flow = pd.DataFrame([annual_capex], index=["Capital Expenditure"], columns=annual_dates)
    f.quarterly_cashflow = pd.DataFrame(
        [quarterly_capex, quarterly_ocf],
        index=["Capital Expenditure", "Operating Cash Flow"], columns=quarterly_dates)
    return f


def test_averages_ttm_plus_fiscal_years():
    f = _fetcher(
        annual_capex=[-90.0, -50.0, -30.0, -30.0, float("nan")],
        quarterly_capex=[-50.0, -40.0, -35.0, -25.0, -20.0],
        quarterly_ocf=[60.0, 50.0, 45.0, 45.0, 40.0],
    )
    r = f.get_normalized_free_cash_flow()
    assert [p["period"] for p in r["capex_periods"]] == ["TTM", "FY2025", "FY2024", "FY2023", "FY2022"]
    assert r["capex_periods"][0]["capex"] == 150.0          # sum of latest four quarters
    assert r["avg_capex"] == pytest.approx((150 + 90 + 50 + 30 + 30) / 5)
    assert r["ocf"] == 200.0                                # TTM OCF
    assert r["normalized_fcf"] == pytest.approx(200.0 - 70.0)


def test_skips_ttm_when_latest_quarter_is_fiscal_year_end():
    dates = pd.to_datetime(["2025-12-31", "2025-09-30", "2025-06-30", "2025-03-31"])
    f = _fetcher(
        annual_capex=[-90.0, -50.0, -30.0],
        quarterly_capex=[-30.0, -20.0, -20.0, -20.0],
        quarterly_ocf=[50.0, 50.0, 50.0, 50.0],
        quarterly_dates=dates,
    )
    r = f.get_normalized_free_cash_flow()
    assert [p["period"] for p in r["capex_periods"]] == ["FY2025", "FY2024", "FY2023"]
    assert r["normalized_fcf"] == pytest.approx(200.0 - (90 + 50 + 30) / 3)


def test_returns_none_with_too_few_periods():
    f = _fetcher(
        annual_capex=[-90.0],
        quarterly_capex=[-30.0, -20.0],
        quarterly_ocf=[50.0, 50.0],
    )
    assert f.get_normalized_free_cash_flow() is None


def test_returns_none_without_capex_row():
    f = _fetcher(annual_capex=[-1.0], quarterly_capex=[-1.0], quarterly_ocf=[1.0])
    f.cash_flow = pd.DataFrame()
    assert f.get_normalized_free_cash_flow() is None
