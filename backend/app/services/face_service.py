"""
Compares 128-dimensional face descriptors produced client-side by
face-api.js (running fully in the browser via webcam). The backend never
sees a photo -- only the numeric descriptor vector -- and never runs face
detection itself; it just measures the distance between "enrolled" and
"live" descriptors.

This is the same comparison approach real face-api.js-based systems use:
Euclidean distance below a threshold (~0.6 is the standard, empirically
validated threshold for this library's recognition model) means "same
person".
"""
import math
from typing import List, Optional

MATCH_THRESHOLD = 0.5


def euclidean_distance(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Descriptor length mismatch")
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def is_match(enrolled: Optional[List[float]], live: List[float]) -> tuple[bool, Optional[float]]:
    if not enrolled:
        return False, None
    distance = euclidean_distance(enrolled, live)
    return distance < MATCH_THRESHOLD, round(distance, 4)