"""Train/test split source-of-truth shared by Phase 8 (training pipeline) and
Phase 9 (backtester).

Detections with confirmation_date >= TRAIN_TEST_CUTOFF are EXCLUDED from
training and form the out-of-sample backtest slice (CONTEXT D-07).
Phase 9 may revise this date; this file remains the single source.
"""
# ── Train/test split (D-07) ─────────────────────────────────────────────────
TRAIN_TEST_CUTOFF = "2024-01-01"  # placeholder; Phase 9 may revise
