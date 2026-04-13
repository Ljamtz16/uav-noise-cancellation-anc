from __future__ import annotations

import numpy as np


def generate_secondary_path(length: int = 32, delay_samples: int = 2, attenuation: float = 0.8, seed: int | None = 42) -> np.ndarray:
    """
    Generate a realistic secondary path impulse response.
    
    Simulates: loudspeaker delay + acoustic propagation + attenuation.
    
    Args:
        length: Total impulse response length
        delay_samples: Propagation delay (samples)
        attenuation: Amplitude decay factor (0 < attenuation <= 1)
        seed: Random seed for reproducibility
    
    Returns:
        Impulse response array of shape (length,)
    """
    if length <= 0:
        raise ValueError("length must be positive")
    if delay_samples >= length:
        raise ValueError("delay_samples must be less than length")
    if attenuation <= 0 or attenuation > 1:
        raise ValueError("attenuation must be in (0, 1]")

    rng = np.random.default_rng(seed)
    h = np.zeros(length)

    # Delayed primary component (direct path through loudspeaker)
    if delay_samples < length:
        h[delay_samples] = attenuation

    # Small secondary reflections (acoustic environment)
    if delay_samples + 5 < length:
        h[delay_samples + 5] = 0.1 * attenuation * rng.normal()
    if delay_samples + 10 < length:
        h[delay_samples + 10] = 0.05 * attenuation * rng.normal()

    return h


def apply_secondary_path(signal: np.ndarray, h: np.ndarray, mode: str = "same") -> np.ndarray:
    """
    Apply secondary path impulse response to a signal.
    
    Args:
        signal: Input signal (1D array)
        h: Secondary path impulse response
        mode: 'same' (default) or 'full' for convolution mode
    
    Returns:
        Filtered signal
    """
    if signal.ndim != 1 or h.ndim != 1:
        raise ValueError("signal and h must be 1D")

    filtered = np.convolve(signal, h, mode=mode)
    if mode == "same":
        filtered = filtered[: len(signal)]
    return filtered
