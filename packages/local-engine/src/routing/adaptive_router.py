"""Adaptive routing - benchmarks hardware and network to choose ASR strategy."""
import logging
import platform
import time

import numpy as np

logger = logging.getLogger(__name__)


class AdaptiveRouter:
    """Benchmarks hardware at startup and recommends ASR strategy."""

    STRATEGIES = {
        "local_full": "distil-large-v3",
        "local_medium": "small",
        "local_lite": "tiny",
        "cloud": "cloud",
    }

    def __init__(self):
        self._hw_score = self._benchmark_hardware()
        self._strategy = self._choose_strategy()
        logger.info(f"Adaptive router: strategy={self._strategy}, hw_score={self._hw_score:.2f}")

    @property
    def strategy(self) -> str:
        return self._strategy

    @property
    def recommended_model(self) -> str:
        return self.STRATEGIES.get(self._strategy, "small")

    def _benchmark_hardware(self) -> float:
        """Quick hardware benchmark. Returns a score 0-1 (higher = better)."""
        import os

        score = 0.0

        # CPU cores
        cpu_count = os.cpu_count() or 2
        if cpu_count >= 8:
            score += 0.4
        elif cpu_count >= 4:
            score += 0.25
        else:
            score += 0.1

        # Available memory (rough estimate)
        try:
            import psutil
            mem_gb = psutil.virtual_memory().total / (1024 ** 3)
            if mem_gb >= 16:
                score += 0.3
            elif mem_gb >= 8:
                score += 0.2
            else:
                score += 0.1
        except ImportError:
            # Default assumption
            score += 0.15

        # Platform bonus (Apple Silicon is fast for Whisper)
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            score += 0.3
        else:
            score += 0.15

        return min(score, 1.0)

    def _choose_strategy(self) -> str:
        if self._hw_score >= 0.7:
            return "local_full"
        elif self._hw_score >= 0.4:
            return "local_medium"
        else:
            return "local_lite"
