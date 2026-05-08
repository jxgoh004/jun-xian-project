"""Unit checks on the trained ONNX artifacts — TRAIN-04.

The actual clean-venv inference round-trip lives in scripts/pattern_scanner/verify_onnx.py
(Plan 05) — it requires creating a temp venv, which is too slow / brittle for the unit suite.
"""
from __future__ import annotations

import json
from pathlib import Path

ONNX_PATH = Path("models/inside_bar_v1.onnx")
SUMMARY_PATH = Path("models/training_summary.json")


def test_onnx_file_exists():
    assert ONNX_PATH.exists(), f"{ONNX_PATH} not committed — run train.py first"
    size = ONNX_PATH.stat().st_size
    assert 1_000_000 <= size <= 50_000_000, f"unexpected size {size} for YOLOv8n ONNX"


def test_opset_recorded():
    assert SUMMARY_PATH.exists(), f"{SUMMARY_PATH} not committed — run train.py first"
    payload = json.loads(SUMMARY_PATH.read_text())
    assert payload["opset"] == 12, f"opset != 12: {payload['opset']}"
    assert payload["imgsz"] == 640
    assert payload["fliplr"] == 0.0


def test_manifest_sha256_round_trip(tmp_path, monkeypatch, synthetic_ohlc):
    """Re-run the generator twice at tmp_path with the same seed against a
    monkeypatched synthetic _fetch_ohlc; concat_sha256 must be byte-identical.

    Proves seeded determinism without a yfinance fetch (small slice ~ 60 bars,
    runs in milliseconds). The committed manifest's concat_sha256 sanity
    (length 64, hex chars only) is also asserted as a tripwire.
    """
    import scripts.pattern_scanner.generate_training_data as gen_mod
    from scripts.pattern_scanner.generate_training_data import main

    # Build a 60-bar synthetic frame deterministically.
    rows = [(100.0 + i * 0.1, 100.5 + i * 0.1, 99.5 + i * 0.1, 100.2 + i * 0.1) for i in range(60)]
    df = synthetic_ohlc(rows)

    def fake_fetch(ticker, period="10y"):
        return df.copy()

    monkeypatch.setattr(gen_mod, "_fetch_ohlc", fake_fetch)
    monkeypatch.setattr(gen_mod, "_load_tickers", lambda limit: ["TST1"])
    monkeypatch.setattr(gen_mod.time, "sleep", lambda *_: None)

    ds_a = tmp_path / "a"; m_a = tmp_path / "ma"
    ds_b = tmp_path / "b"; m_b = tmp_path / "mb"

    rc_a = main(["--seed", "42", "--limit", "1",
                 "--dataset-root", str(ds_a), "--models-root", str(m_a)])
    rc_b = main(["--seed", "42", "--limit", "1",
                 "--dataset-root", str(ds_b), "--models-root", str(m_b)])
    assert rc_a == 0 and rc_b == 0

    sha_a = json.loads((ds_a / "dataset_manifest.json").read_text())["concat_sha256"]
    sha_b = json.loads((ds_b / "dataset_manifest.json").read_text())["concat_sha256"]
    assert sha_a == sha_b, f"determinism broken: {sha_a} != {sha_b}"

    # Tripwire: committed manifest sanity (still useful as a smoke check)
    committed = json.loads(Path("models/dataset_manifest.json").read_text())
    assert len(committed["concat_sha256"]) == 64
    assert all(c in "0123456789abcdef" for c in committed["concat_sha256"])
    assert committed["seed"] == 42, f"expected seed 42 from Plan 04 run; got {committed['seed']}"
