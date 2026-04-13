from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy import signal


def list_uavirbase_files(dataset_root: Path) -> list[Path]:
    if not dataset_root.exists():
        return []
    return sorted(dataset_root.rglob("*.wav"))


def load_uavirbase_sample(
    path: str | Path,
    target_fs: int | None = None,
    max_seconds: float | None = None,
    mic_id: str | None = None,
    normalize: bool = True,
    mono: bool = True,
) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"UaVirBASE file not found: {file_path}")

    x, fs = sf.read(file_path)
    if mono and x.ndim == 2:
        x = np.mean(x, axis=1)

    if target_fs is not None and fs != target_fs:
        target_len = int(len(x) * target_fs / fs)
        x = signal.resample(x, target_len)
        fs = target_fs

    if max_seconds is not None and max_seconds > 0:
        max_samples = int(max_seconds * fs)
        x = x[:max_samples]

    if normalize:
        peak = np.max(np.abs(x)) if len(x) else 0.0
        if peak > 0:
            x = x / peak

    return {
        "signal": np.asarray(x, dtype=float),
        "fs": int(fs),
        "mic_id": mic_id,
        "distance": None,
        "azimuth": None,
        "altitude": None,
        "filename": file_path.name,
        "filepath": str(file_path),
        "dataset": "UaVirBASE",
    }
