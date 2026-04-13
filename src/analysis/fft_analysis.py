from __future__ import annotations

import numpy as np


def compute_fft(signal: np.ndarray, fs: int) -> tuple[np.ndarray, np.ndarray]:
    if fs <= 0:
        raise ValueError("fs must be positive")
    if signal.ndim != 1:
        raise ValueError("signal must be 1D")

    n = len(signal)
    freq = np.fft.rfftfreq(n, d=1 / fs)
    mag = np.abs(np.fft.rfft(signal)) / n
    return freq, mag


def dominant_frequency(signal: np.ndarray, fs: int, min_hz: float = 20.0) -> float:
    freq, mag = compute_fft(signal, fs)
    valid = freq >= min_hz
    idx = np.argmax(mag[valid])
    return float(freq[valid][idx])
