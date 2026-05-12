"""One-shot helper to project a full backtest cache into a small aggregates-only file.

Phase 10 D-10: The full Phase 9 cache (_dev/backtest_cache.json) is gitignored (27.8 MB).
The GHA runner does not have it. Instead, a small _backtest_aggregates.json (< 50 KB)
is committed at docs/projects/patterns/ and refreshed manually when the backtest is rerun.

Usage:
    python -m scripts.pattern_scanner.export_aggregates \
        --in _dev/backtest_cache.json \
        --out docs/projects/patterns/_backtest_aggregates.json \
        --strategy 1to2_rr_cluster_low_stop \
        --sample out_of_sample
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def project_aggregates(cache: dict, strategy: str, sample: str) -> dict:
    """Pure: project a full backtest cache into the small aggregates-only shape.

    Phase 10 D-10/D-11 contract. Strategy defaults to '1to2_rr_cluster_low_stop'
    (filtered, per D-04), sample defaults to 'out_of_sample' (per D-11).
    """
    if "strategies" not in cache:
        raise KeyError("cache missing 'strategies' key; not a valid backtest cache")
    if strategy not in cache["strategies"]:
        raise KeyError(
            f"strategy {strategy!r} not in cache; available: {list(cache['strategies'])}"
        )
    strat = cache["strategies"][strategy][sample]
    return {
        "schema_version": 1,
        "extracted_from": "_dev/backtest_cache.json",
        "extracted_at": cache.get("generated_at"),
        "train_test_cutoff": cache.get("train_test_cutoff"),
        "onnx_sha256": cache.get("onnx_sha256"),
        "strategy": strategy,
        "sample": sample,
        "aggregates": strat["aggregates"],
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Project a Phase 9 backtest cache into Phase 10 _backtest_aggregates.json."
    )
    p.add_argument(
        "--in",
        dest="inp",
        type=Path,
        required=True,
        help="Path to _dev/backtest_cache.json (Phase 9 output, gitignored).",
    )
    p.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Path to docs/projects/patterns/_backtest_aggregates.json.",
    )
    p.add_argument(
        "--strategy",
        default="1to2_rr_cluster_low_stop",
        help="Strategy key in cache.strategies (default: filtered, per D-04).",
    )
    p.add_argument(
        "--sample",
        default="out_of_sample",
        choices=["in_sample", "out_of_sample"],
        help="Sample slice (default: out_of_sample per D-11).",
    )
    args = p.parse_args(argv)

    if not args.inp.exists():
        print(f"[export_aggregates] FAIL: {args.inp} does not exist", file=sys.stderr)
        return 2
    cache = json.loads(args.inp.read_text(encoding="utf-8"))
    out = project_aggregates(cache, args.strategy, args.sample)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # ME-05: atomic write via sibling tmp + os.replace. The output file is
    # git-tracked; a partial write here would commit a corrupted JSON. Mirrors
    # the contract of run_pipeline._atomic_write_json (kept local instead of
    # imported to avoid a cross-module dependency on a script's internals).
    tmp = args.out.with_suffix(args.out.suffix + ".tmp")
    try:
        tmp.write_text(
            json.dumps(out, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, args.out)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
    n_all = out["aggregates"].get("all", {}).get("n", 0)
    print(
        f"[export_aggregates] OK: wrote {args.out} "
        f"(strategy={args.strategy} sample={args.sample} n={n_all})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
