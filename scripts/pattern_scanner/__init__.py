"""Pattern scanner package — inside bar spring detection.

Public API:
    from scripts.pattern_scanner.detector import detect, Detection
"""
from .detector import Detection, detect

__all__ = ["Detection", "detect"]
