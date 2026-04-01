"""Audio utility functions."""
import numpy as np


def resample(audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    """Resample audio from source_rate to target_rate."""
    if source_rate == target_rate:
        return audio
    from scipy.signal import resample as scipy_resample
    num_samples = int(len(audio) * target_rate / source_rate)
    return scipy_resample(audio, num_samples).astype(np.float32)


def stereo_to_mono(audio: np.ndarray) -> np.ndarray:
    """Convert stereo audio to mono by averaging channels."""
    if audio.ndim == 1:
        return audio
    return audio.mean(axis=-1).astype(np.float32)


def normalize(audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """Normalize audio to target peak level."""
    peak = np.max(np.abs(audio))
    if peak > 0:
        return (audio * target_peak / peak).astype(np.float32)
    return audio


def float32_to_int16(audio: np.ndarray) -> np.ndarray:
    """Convert float32 [-1, 1] to int16."""
    return (audio * 32767).clip(-32768, 32767).astype(np.int16)


def int16_to_float32(audio: np.ndarray) -> np.ndarray:
    """Convert int16 to float32 [-1, 1]."""
    return audio.astype(np.float32) / 32768.0


def compute_rms(audio: np.ndarray) -> float:
    """Compute RMS energy of audio."""
    return float(np.sqrt(np.mean(audio ** 2)))


def detect_silence(audio: np.ndarray, threshold: float = 0.01) -> bool:
    """Check if audio is silent based on RMS threshold."""
    return compute_rms(audio) < threshold
