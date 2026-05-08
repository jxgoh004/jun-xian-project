"""T-9-01: CLI ticker validation rejects malformed tokens before yfinance call."""
import argparse

import pytest

from scripts.pattern_scanner.backtest import _parse_tickers_arg, _validate_ticker_token


@pytest.mark.parametrize("bad_token", [
    "../etc/passwd",
    "AAA;rm -rf",
    "",
    "TOOLONGTICKER",     # 13 chars, > 10 limit
    "AB CD",             # whitespace inside (after strip still has space)
    "AB|CD",             # pipe
    "AB$CD",             # dollar
])
def test_invalid_ticker_rejected(bad_token):
    """Per T-9-01 mitigation: tokens that fail _TICKER_RE must raise ArgumentTypeError."""
    with pytest.raises(argparse.ArgumentTypeError):
        _validate_ticker_token(bad_token)


@pytest.mark.parametrize("good_token,expected", [
    ("AAPL", "AAPL"),
    ("aapl", "AAPL"),         # lowercase upper()d before regex (parser is case-permissive)
    ("BRK.B", "BRK.B"),
    ("GOOG", "GOOG"),
    ("brk-b", "BRK-B"),
])
def test_valid_ticker_accepted(good_token, expected):
    assert _validate_ticker_token(good_token) == expected


def test_parse_tickers_arg_all_passthrough():
    assert _parse_tickers_arg("all") == "all"


def test_parse_tickers_arg_comma_list():
    assert _parse_tickers_arg("AAPL,MSFT,brk.b") == ["AAPL", "MSFT", "BRK.B"]


def test_parse_tickers_arg_rejects_bad_in_list():
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_tickers_arg("AAPL,../etc/passwd,MSFT")
