from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
import streamlit as st
from scipy import signal

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.fft_analysis import compute_fft, dominant_frequency
from src.analysis.metrics import noise_reduction_db
from src.analysis.psd_analysis import compute_psd
from src.anc.fxlms import FxLMS
from src.anc.lms import LMS
from src.data.uavirbase_loader import list_uavirbase_files, load_uavirbase_sample
from src.signal.generate_signal import generate_uav_signal
from src.simulation.secondary_path import generate_secondary_path


def _run_lms(x: np.ndarray, mu: float, taps: int) -> tuple[np.ndarray, np.ndarray]:
    model = LMS(mu=mu, filter_order=taps)
    y = np.zeros_like(x)
    e = np.zeros_like(x)
    for index, sample in enumerate(x):
        y[index], e[index] = model.adapt(desired=float(sample), input_sample=float(sample))
    return y, e


def _run_fxlms(
    x: np.ndarray,
    mu: float,
    taps: int,
    secondary_on: bool,
    sec_len: int,
    sec_delay: int,
    sec_att: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sec_path = np.array([1.0])
    if secondary_on:
        sec_path = generate_secondary_path(
            length=sec_len,
            delay_samples=sec_delay,
            attenuation=sec_att,
            seed=42,
        )

    model = FxLMS(mu=mu, filter_order=taps, secondary_path=sec_path)
    y = np.zeros_like(x)
    e = np.zeros_like(x)
    for index, sample in enumerate(x):
        y[index], e[index] = model.adapt(desired=float(sample), input_sample=float(sample))

    return y, e, sec_path


def _mse_curve(error_signal: np.ndarray) -> np.ndarray:
    squared = error_signal**2
    return np.cumsum(squared) / (np.arange(len(squared)) + 1)


def _safe_mse_curve(error_signal: np.ndarray) -> np.ndarray:
    cleaned = np.nan_to_num(error_signal, nan=0.0, posinf=0.0, neginf=0.0)
    return _mse_curve(cleaned)


def _load_audio(file_bytes: bytes, target_fs: int, max_seconds: float) -> tuple[np.ndarray, int]:
    audio, fs = sf.read(io.BytesIO(file_bytes))
    if audio.ndim == 2:
        audio = np.mean(audio, axis=1)

    if fs != target_fs:
        target_len = int(len(audio) * target_fs / fs)
        audio = signal.resample(audio, target_len)
        fs = target_fs

    max_samples = int(max_seconds * fs)
    audio = audio[:max_samples]

    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak

    return audio.astype(float), fs


def _safe_noise_reduction_db(original: np.ndarray, error: np.ndarray) -> float:
    if not np.all(np.isfinite(error)):
        return float("nan")
    try:
        return noise_reduction_db(original, error)
    except Exception:
        return float("nan")


def _fmt_db(value: float) -> str:
    return f"{value:.2f} dB" if np.isfinite(value) else "N/A"


st.set_page_config(page_title="UAV ANC Lab", layout="wide")
st.title("UAV Acoustic Digital Twin + ANC Lab")
st.caption("MVP experimental: simulación controlada + audio real, con comparación LMS vs FxLMS.")

with st.sidebar:
    st.header("Entrada")
    mode = st.radio("Modo", ["Simulado", "Audio real", "UaVirBASE"], index=0)
    fs = st.slider("Frecuencia de muestreo (Hz)", min_value=4000, max_value=48000, value=8000, step=1000)
    mu = st.slider("μ (learning rate)", min_value=0.001, max_value=0.05, value=0.01, step=0.001)
    taps = st.slider("Longitud del filtro (taps)", min_value=16, max_value=256, value=64, step=16)

    secondary_on = st.toggle("Secondary path ON", value=True)
    sec_len = st.slider("Secondary path length", min_value=8, max_value=128, value=32, step=8)
    sec_delay = st.slider("Secondary path delay", min_value=0, max_value=16, value=2, step=1)
    sec_att = st.slider("Secondary attenuation", min_value=0.1, max_value=1.0, value=0.8, step=0.05)

signal_data: np.ndarray
time_axis: np.ndarray
f_bpf_theoretical: float | None = None
metadata: dict[str, Any] = {}

if mode == "Simulado":
    with st.sidebar:
        rpm = st.slider("RPM", min_value=1000, max_value=12000, value=6000, step=100)
        blades = st.slider("Número de aspas", min_value=2, max_value=6, value=2, step=1)
        duration = st.slider("Duración (s)", min_value=1.0, max_value=10.0, value=2.0, step=0.5)
        harmonics = st.slider("Armónicos", min_value=1, max_value=8, value=3, step=1)
        noise_std = st.slider("Ruido broadband (σ)", min_value=0.0, max_value=0.5, value=0.2, step=0.01)

    harmonic_amplitudes = tuple(1.0 / harmonic for harmonic in range(1, harmonics + 1))
    time_axis, signal_data, f_bpf_theoretical = generate_uav_signal(
        fs=fs,
        duration=duration,
        rpm=rpm,
        n_blades=blades,
        harmonic_amplitudes=harmonic_amplitudes,
        noise_std=noise_std,
        seed=42,
    )
else:
    if mode == "Audio real":
        with st.sidebar:
            max_seconds = st.slider("Duración máxima a analizar (s)", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
            uploaded = st.file_uploader("Sube WAV", type=["wav"])
            recorded = st.audio_input("O graba audio")

        raw_audio_bytes = None
        if uploaded is not None:
            raw_audio_bytes = uploaded.read()
        elif recorded is not None:
            raw_audio_bytes = recorded.read()

        if raw_audio_bytes is None:
            st.info("Sube o graba un archivo WAV para ejecutar el análisis en modo audio real.")
            st.stop()

        signal_data, fs = _load_audio(raw_audio_bytes, target_fs=fs, max_seconds=max_seconds)
        time_axis = np.arange(len(signal_data)) / fs
    else:
        default_root = ROOT / "data" / "raw" / "uavirbase"
        with st.sidebar:
            dataset_root_str = st.text_input("Ruta carpeta UaVirBASE", value=str(default_root))
            max_seconds = st.slider("Duración máxima a analizar (s)", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
            mic_id = st.text_input("Mic ID (opcional)", value="")

        dataset_root = Path(dataset_root_str)
        files = list_uavirbase_files(dataset_root)
        if not files:
            st.warning(
                "No se encontraron archivos WAV en UaVirBASE. Coloca archivos en data/raw/uavirbase/ o ajusta la ruta."
            )
            st.stop()

        selected_path = st.sidebar.selectbox("Archivo UaVirBASE", options=files, format_func=lambda path: path.name)
        sample = load_uavirbase_sample(
            selected_path,
            target_fs=fs,
            max_seconds=max_seconds,
            mic_id=mic_id or None,
            normalize=True,
            mono=True,
        )
        signal_data = sample["signal"]
        fs = int(sample["fs"])
        metadata = sample
        time_axis = np.arange(len(signal_data)) / fs

lms_output, lms_error = _run_lms(signal_data, mu=mu, taps=taps)
fxlms_output, fxlms_error, sec_path = _run_fxlms(
    signal_data,
    mu=mu,
    taps=taps,
    secondary_on=secondary_on,
    sec_len=sec_len,
    sec_delay=min(sec_delay, sec_len - 1),
    sec_att=sec_att,
)

fft_f, fft_x = compute_fft(signal_data, fs)
_, fft_lms_e = compute_fft(np.nan_to_num(lms_error), fs)
_, fft_fxlms_e = compute_fft(np.nan_to_num(fxlms_error), fs)

psd_f, psd_x = compute_psd(signal_data, fs)
_, psd_lms_e = compute_psd(np.nan_to_num(lms_error), fs)
_, psd_fxlms_e = compute_psd(np.nan_to_num(fxlms_error), fs)

lms_db = _safe_noise_reduction_db(signal_data, lms_error)
fxlms_db = _safe_noise_reduction_db(signal_data, fxlms_error)
dominant_hz = dominant_frequency(signal_data, fs)

if f_bpf_theoretical is not None:
    dominant_error_hz = abs(dominant_hz - f_bpf_theoretical)
else:
    dominant_error_hz = np.nan

status = "Estable" if np.isfinite(lms_db) and np.isfinite(fxlms_db) else "Inestable"
if status == "Inestable":
    st.warning("Se detectó inestabilidad numérica (NaN/Inf). Reduce μ o taps para recuperar convergencia.")

tab_input, tab_time, tab_spec, tab_compare, tab_metrics = st.tabs(
    ["Entrada", "Señal temporal", "FFT/PSD", "LMS vs FxLMS", "Métricas"]
)

with tab_input:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Configuración activa")
        st.write(
            {
                "modo": mode,
                "fs": fs,
                "mu": mu,
                "taps": taps,
                "secondary_on": secondary_on,
                "status": status,
            }
        )
        if mode == "UaVirBASE":
            st.write(
                {
                    "filename": metadata.get("filename"),
                    "dataset": metadata.get("dataset"),
                    "mic_id": metadata.get("mic_id"),
                }
            )
    with col2:
        st.subheader("Secondary path")
        fig, ax = plt.subplots(figsize=(6, 2.2))
        ax.plot(sec_path)
        ax.set_title("Impulse response")
        ax.set_xlabel("n")
        ax.set_ylabel("h[n]")
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
        plt.close(fig)

with tab_time:
    sample_view = min(len(signal_data), int(0.5 * fs))
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(time_axis[:sample_view], signal_data[:sample_view], label="Original", linewidth=1)
    ax.plot(time_axis[:sample_view], np.nan_to_num(lms_error[:sample_view]), label=f"Error LMS ({_fmt_db(lms_db)})", linewidth=1)
    ax.plot(time_axis[:sample_view], np.nan_to_num(fxlms_error[:sample_view]), label=f"Error FxLMS ({_fmt_db(fxlms_db)})", linewidth=1)
    ax.set_xlabel("Tiempo (s)")
    ax.set_ylabel("Amplitud")
    ax.set_title("Comparación temporal")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)
    plt.close(fig)

with tab_spec:
    col1, col2 = st.columns(2)
    with col1:
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.plot(fft_f, fft_x, label="Original")
        ax.plot(fft_f, fft_lms_e, label="LMS error")
        ax.plot(fft_f, fft_fxlms_e, label="FxLMS error")
        ax.set_xlim(0, min(2000, fs / 2))
        ax.set_title("FFT")
        ax.set_xlabel("Frecuencia (Hz)")
        ax.set_ylabel("Magnitud")
        ax.grid(True, alpha=0.3)
        ax.legend()
        st.pyplot(fig)
        plt.close(fig)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.semilogy(psd_f, psd_x, label="Original")
        ax.semilogy(psd_f, psd_lms_e, label="LMS error")
        ax.semilogy(psd_f, psd_fxlms_e, label="FxLMS error")
        ax.set_xlim(0, min(2000, fs / 2))
        ax.set_title("PSD (Welch)")
        ax.set_xlabel("Frecuencia (Hz)")
        ax.set_ylabel("Potencia")
        ax.grid(True, alpha=0.3)
        ax.legend()
        st.pyplot(fig)
        plt.close(fig)

with tab_compare:
    col1, col2 = st.columns(2)
    with col1:
        lms_mse = _safe_mse_curve(lms_error)
        fxlms_mse = _safe_mse_curve(fxlms_error)
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.semilogy(lms_mse, label="LMS")
        ax.semilogy(fxlms_mse, label="FxLMS")
        ax.set_title("Convergencia MSE")
        ax.set_xlabel("Muestra")
        ax.set_ylabel("MSE acumulado")
        ax.grid(True, alpha=0.3)
        ax.legend()
        st.pyplot(fig)
        plt.close(fig)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 3.5))
        bar_values = [lms_db if np.isfinite(lms_db) else 0.0, fxlms_db if np.isfinite(fxlms_db) else 0.0]
        ax.bar(["LMS", "FxLMS"], bar_values)
        ax.set_ylabel("Reducción de ruido (dB)")
        ax.set_title("Comparación de desempeño")
        ax.grid(True, axis="y", alpha=0.3)
        st.pyplot(fig)
        plt.close(fig)

with tab_metrics:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Reducción LMS", _fmt_db(lms_db))
    m2.metric("Reducción FxLMS", _fmt_db(fxlms_db))
    m3.metric("Frecuencia dominante", f"{dominant_hz:.2f} Hz")
    m4.metric("Estado", status)

    if np.isnan(dominant_error_hz):
        st.write("Error de frecuencia dominante: N/A (modo audio real sin BPF teórica)")
    else:
        st.write(f"Error de frecuencia dominante respecto a BPF teórica: {dominant_error_hz:.2f} Hz")

    st.write(
        {
            "mse_lms_final": float(_safe_mse_curve(lms_error)[-1]),
            "mse_fxlms_final": float(_safe_mse_curve(fxlms_error)[-1]),
            "delta_db_lms_vs_fxlms": float(fxlms_db - lms_db) if np.isfinite(lms_db) and np.isfinite(fxlms_db) else "N/A",
        }
    )
