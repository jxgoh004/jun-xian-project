"""Unit tests for scripts.pattern_scanner.generate_training_data — TRAIN-02 + TRAIN-03 (Plan 03 fills these in)."""
from __future__ import annotations
import pytest

pytestmark = pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 03 (dataset generator)")

def test_yolo_directory_layout():
    """Generator emits images/{train,val} + labels/{train,val} + data.yaml under DATASET_ROOT."""

def test_positive_label_format():
    """Positive labels are '0 cx cy w h' with all values normalized 0..1."""

def test_style_randomization_used():
    """Every sample has a style attribute; >=2 distinct style names are seen across N samples."""

def test_cutoff_enforced():
    """No detection with confirmation_date >= TRAIN_TEST_CUTOFF appears in the generated dataset."""

def test_neg_pos_ratio_capped():
    """len(negatives) / len(positives) <= 10 in the generated manifest."""

def test_negative_labels_empty():
    """Negative samples have an existing .txt file with zero bytes."""

def test_hard_negative_set_difference():
    """Hard-negative pool = (filters-disabled detect()) MINUS real positives, keyed on (ticker, mother_bar_index, confirmation_bar_index)."""

def test_manifest_sha256_consistent():
    """Manifest concat_sha256 equals sha256-of-concat of the actual PNG sha256s on disk."""
