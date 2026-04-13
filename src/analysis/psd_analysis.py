from __future__ import annotations

import numpy as np
from scipy import signal


def compute_psd(x: np.ndarray, fs: int, nperseg: int = 1024) -> tuple[np.ndarray, np.ndarray]:
    if fs <= 0:
        raise ValueError("fs must be positive")
    if x.ndim != 1:
        raise ValueError("x must be 1D")

    f, pxx = signal.welch(x, fs=fs, nperseg=min(nperseg, len(x)))
    return f, pxx
