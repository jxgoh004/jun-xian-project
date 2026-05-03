"""Offline trainer + ONNX exporter for the inside bar spring detector (CONTEXT D-20).

Run inside .venv WITH requirements-training.txt installed (locally or on Colab).
NEVER imported by any GitHub Actions workflow — torch + ultralytics are training-only.

CLI:
    python scripts/pattern_scanner/train.py --seed 42 --epochs 100 --patience 20

Outputs:
    models/inside_bar_v1.onnx              (committed, ~6-12 MB)
    models/training_summary.json           (committed, hyperparams + metrics + opset)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

DATASET_ROOT = Path("_dev/training_dataset")
DATA_YAML = DATASET_ROOT / "data.yaml"
ONNX_OUT = Path("models/inside_bar_v1.onnx")
TRAINING_SUMMARY = Path("models/training_summary.json")
OPSET = 12
IMG_SIZE = 640
FLIPLR = 0.0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Train YOLOv8n + export ONNX (offline only).")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--batch", type=int, default=-1, help="-1 = auto-batch")
    p.add_argument("--patience", type=int, default=20)
    args = p.parse_args(argv)

    if not DATA_YAML.exists():
        print(f"[train] FAIL: {DATA_YAML} not found. Run generate_training_data.py first.",
              file=sys.stderr)
        return 2

    from ultralytics import YOLO

    t0 = time.monotonic()
    model = YOLO("yolov8n.pt")
    results = model.train(
        data=str(DATA_YAML),
        imgsz=IMG_SIZE,
        epochs=args.epochs,
        batch=args.batch,
        seed=args.seed,
        deterministic=True,
        fliplr=FLIPLR,
        patience=args.patience,
    )
    wall_time_s = time.monotonic() - t0

    print(f"[train] best mAP50: {float(results.box.map50):.4f}")
    print(f"[train] best mAP50-95: {float(results.box.map):.4f}")
    print(f"[train] save_dir: {results.save_dir}")
    print(f"[train] wall_time_s: {wall_time_s:.1f}")

    best_pt = Path(results.save_dir) / "weights" / "best.pt"
    best = YOLO(str(best_pt))
    onnx_path = best.export(
        format="onnx",
        opset=OPSET,
        dynamic=False,
        imgsz=IMG_SIZE,
        simplify=True,
    )
    print(f"[export] ONNX written: {onnx_path}")
    print(f"[export] OPSET: {OPSET}  (logged to stdout per D-17)")

    ONNX_OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(str(onnx_path), str(ONNX_OUT))
    print(f"[export] copied to {ONNX_OUT}")

    summary = {
        "opset": OPSET,
        "imgsz": IMG_SIZE,
        "fliplr": FLIPLR,
        "cls_pw": 1.0,
        "seed": args.seed,
        "epochs_run": int(getattr(results, "epoch", args.epochs - 1)) + 1,
        "best_map50": float(results.box.map50),
        "best_map50_95": float(results.box.map),
        "wall_time_s": wall_time_s,
        "ultralytics_save_dir": str(results.save_dir),
    }
    TRAINING_SUMMARY.write_text(json.dumps(summary, indent=2))
    print(f"[done] training_summary.json written: {TRAINING_SUMMARY}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
