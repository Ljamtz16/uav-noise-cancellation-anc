from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np


def plot_time_series(t: np.ndarray, x: np.ndarray, title: str, xlabel: str = "Time [s]", ylabel: str = "Amplitude") -> None:
    plt.figure(figsize=(10, 4))
    plt.plot(t, x)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()


def plot_spectrum(freq: np.ndarray, mag: np.ndarray, title: str) -> None:
    plt.figure(figsize=(10, 4))
    plt.plot(freq, mag)
    plt.title(title)
    plt.xlabel("Frequency [Hz]")
    plt.ylabel("Magnitude")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
