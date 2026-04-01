"""Tests for RingBuffer."""
import numpy as np
from src.utils.ring_buffer import RingBuffer


def test_basic_append_and_get():
    buf = RingBuffer(max_seconds=1.0, sample_rate=100)
    audio = np.ones(50, dtype=np.float32) * 0.5
    buf.append(audio)

    window = buf.get_window(0.5)
    assert window is not None
    assert len(window) == 50
    assert np.allclose(window, 0.5)


def test_wrap_around():
    buf = RingBuffer(max_seconds=1.0, sample_rate=100)
    # Write 80 samples, then 40 more (wraps at 100)
    buf.append(np.ones(80, dtype=np.float32) * 1.0)
    buf.append(np.ones(40, dtype=np.float32) * 2.0)

    window = buf.get_window(1.0)
    assert window is not None
    assert len(window) == 100
    # First 20 should be 2.0 (wrapped), then 60 of 1.0, then 20 of 2.0...
    # Actually: last 100 samples = 40 from first batch (1.0) + 40 from second batch (2.0)
    # Wait, total is 120 but buffer is 100, so buffer contains last 100 samples


def test_unprocessed_duration():
    buf = RingBuffer(max_seconds=10.0, sample_rate=16000)
    audio = np.zeros(8000, dtype=np.float32)  # 0.5 seconds
    buf.append(audio)

    assert abs(buf.unprocessed_duration - 0.5) < 0.01

    buf.mark_processed()
    assert buf.unprocessed_duration == 0.0


def test_empty_buffer():
    buf = RingBuffer(max_seconds=1.0, sample_rate=100)
    assert buf.get_window(0.5) is None


def test_reset():
    buf = RingBuffer(max_seconds=1.0, sample_rate=100)
    buf.append(np.ones(50, dtype=np.float32))
    buf.reset()
    assert buf.get_window(0.5) is None
    assert buf.unprocessed_duration == 0.0
