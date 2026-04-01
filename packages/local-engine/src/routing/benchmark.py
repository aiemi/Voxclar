"""Hardware and network benchmarking utilities."""
import logging
import time

import numpy as np

logger = logging.getLogger(__name__)


def benchmark_whisper_rtf(model_size: str = "tiny", duration: float = 5.0) -> float:
    """Run a quick Whisper inference benchmark. Returns Real-Time Factor (RTF).
    RTF < 0.3 = high performance, 0.3-0.8 = medium, > 0.8 = low.
    """
    try:
        from faster_whisper import WhisperModel

        # Generate silent audio
        sample_rate = 16000
        audio = np.zeros(int(sample_rate * duration), dtype=np.float32)
        # Add tiny noise to avoid silence skip
        audio += np.random.randn(len(audio)).astype(np.float32) * 0.001

        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        start = time.perf_counter()
        segments, _ = model.transcribe(audio, beam_size=1, vad_filter=False)
        # Force iteration to actually run inference
        for _ in segments:
            pass
        elapsed = time.perf_counter() - start

        rtf = elapsed / duration
        logger.info(f"Whisper benchmark ({model_size}): RTF={rtf:.3f}, elapsed={elapsed:.2f}s")
        return rtf

    except Exception as e:
        logger.error(f"Whisper benchmark failed: {e}")
        return 1.0  # Assume worst case


def measure_network_latency(url: str = "https://api.deepgram.com", timeout: float = 5.0) -> float:
    """Measure network latency to an endpoint. Returns RTT in milliseconds."""
    try:
        import httpx

        start = time.perf_counter()
        with httpx.Client(timeout=timeout) as client:
            client.head(url)
        rtt = (time.perf_counter() - start) * 1000
        logger.info(f"Network latency to {url}: {rtt:.0f}ms")
        return rtt

    except Exception as e:
        logger.warning(f"Network latency measurement failed: {e}")
        return 9999.0
