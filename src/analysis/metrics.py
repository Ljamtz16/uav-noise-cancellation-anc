from __future__ import annotations

import numpy as np


def power(signal: np.ndarray) -> float:
    if signal.ndim != 1:
        raise ValueError("signal must be 1D")
    return float(np.mean(signal**2))


def noise_reduction_db(original: np.ndarray, error: np.ndarray, eps: float = 1e-12) -> float:
    if original.ndim != 1 or error.ndim != 1:
        raise ValueError("original and error must be 1D")

    p_original = power(original)
    p_error = max(power(error), eps)
    return float(10.0 * np.log10(p_original / p_error))
