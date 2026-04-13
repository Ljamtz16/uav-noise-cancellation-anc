from __future__ import annotations

import numpy as np
from scipy.signal import lfilter


def apply_secondary_path(x: np.ndarray, impulse_response: np.ndarray) -> np.ndarray:
    if x.ndim != 1 or impulse_response.ndim != 1:
        raise ValueError("x and impulse_response must be 1D")
    return lfilter(impulse_response, [1.0], x)


def simple_secondary_path(delay_samples: int = 8, attenuation: float = 0.6) -> np.ndarray:
    if delay_samples < 0:
        raise ValueError("delay_samples must be non-negative")
    if attenuation <= 0:
        raise ValueError("attenuation must be positive")

    h = np.zeros(delay_samples + 1)
    h[-1] = attenuation
    return h
