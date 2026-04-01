"""Lock-free ring buffer for audio data."""
import numpy as np


class RingBuffer:
    """Fixed-size ring buffer for float32 audio samples."""

    def __init__(self, max_seconds: float = 30.0, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._max_samples = int(max_seconds * sample_rate)
        self._buffer = np.zeros(self._max_samples, dtype=np.float32)
        self._write_pos = 0
        self._total_written = 0
        self._last_processed = 0

    def append(self, audio: np.ndarray):
        """Append audio samples to the buffer."""
        n = len(audio)
        if n >= self._max_samples:
            # Audio is larger than buffer - keep only the last max_samples
            self._buffer[:] = audio[-self._max_samples:]
            self._write_pos = 0
            self._total_written += n
            return

        end_pos = self._write_pos + n
        if end_pos <= self._max_samples:
            self._buffer[self._write_pos:end_pos] = audio
        else:
            # Wrap around
            first_part = self._max_samples - self._write_pos
            self._buffer[self._write_pos:] = audio[:first_part]
            self._buffer[:n - first_part] = audio[first_part:]

        self._write_pos = end_pos % self._max_samples
        self._total_written += n

    def get_window(self, seconds: float) -> np.ndarray | None:
        """Get the last N seconds of audio."""
        n_samples = min(int(seconds * self.sample_rate), self._total_written)
        if n_samples == 0:
            return None

        n_samples = min(n_samples, self._max_samples)
        start = (self._write_pos - n_samples) % self._max_samples

        if start < self._write_pos:
            return self._buffer[start:self._write_pos].copy()
        else:
            return np.concatenate([
                self._buffer[start:],
                self._buffer[:self._write_pos],
            ])

    @property
    def unprocessed_duration(self) -> float:
        """Duration of audio not yet processed."""
        unprocessed_samples = self._total_written - self._last_processed
        return unprocessed_samples / self.sample_rate

    def mark_processed(self):
        """Mark current position as processed."""
        self._last_processed = self._total_written

    def reset(self):
        """Reset buffer state."""
        self._buffer[:] = 0
        self._write_pos = 0
        self._total_written = 0
        self._last_processed = 0
