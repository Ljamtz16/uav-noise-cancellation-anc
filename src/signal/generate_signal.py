from __future__ import annotations

import numpy as np

from .bpf_model import blade_passing_frequency


def generate_uav_signal(
    fs: int = 8000,
    duration: float = 2.0,
    rpm: float = 6000,
    n_blades: int = 2,
    harmonic_amplitudes: tuple[float, ...] = (1.0, 0.5, 0.25),
    noise_std: float = 0.2,
    seed: int | None = 42,
) -> tuple[np.ndarray, np.ndarray, float]:
    if fs <= 0:
        raise ValueError("fs must be positive")
    if duration <= 0:
        raise ValueError("duration must be positive")

    n_samples = int(fs * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    f_bpf = blade_passing_frequency(rpm=rpm, n_blades=n_blades)

    signal = np.zeros_like(t)
    for harmonic_index, amplitude in enumerate(harmonic_amplitudes, start=1):
        signal += amplitude * np.sin(2 * np.pi * harmonic_index * f_bpf * t)

    rng = np.random.default_rng(seed)
    signal += noise_std * rng.normal(0, 1, size=n_samples)

    return t, signal, f_bpf
