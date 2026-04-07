"""Windows 系统音频捕获 — WASAPI Loopback。

捕获扬声器输出（对方的声音），核心功能。
使用 WASAPI Loopback 模式捕获系统音频输出，无需虚拟声卡。

捕获策略（按优先级）：
  1. pyaudiowpatch WASAPI Loopback — 最佳方案，直接捕获默认输出设备的回环
  2. sounddevice WASAPI Loopback — 备选，通过 hostapi 查找 loopback 设备
  3. 无可用方案 → method='unavailable'

绝不会 fallback 到麦克风 — 麦克风是另一路独立的音频流。
"""
import logging
import threading
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)


class WindowsCapture:
    """Windows system audio capture using WASAPI loopback."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1,
                 chunk_duration: float = 0.1, callback: Callable | None = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = int(sample_rate * chunk_duration)
        self.callback = callback
        self._running = False
        self._thread: threading.Thread | None = None
        self.method: str = "none"

    def start(self):
        self._running = True
        # Try pyaudiowpatch first, then sounddevice WASAPI, then unavailable
        if self._try_pyaudiowpatch():
            self.method = "wasapi_loopback"
        elif self._try_sounddevice_wasapi():
            self.method = "sounddevice_wasapi"
        else:
            self.method = "unavailable"
            logger.error(
                "WASAPI loopback capture FAILED. Install pyaudiowpatch: "
                "pip install pyaudiowpatch. "
                "System audio capture is required for question detection."
            )
            return

        logger.info(f"Windows system audio capture started: method={self.method}")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

    # ── Strategy 1: pyaudiowpatch (preferred) ────────────────────

    def _try_pyaudiowpatch(self) -> bool:
        try:
            import pyaudiowpatch as pyaudio  # noqa: F401
        except ImportError:
            logger.debug("pyaudiowpatch not installed, trying sounddevice WASAPI")
            return False

        try:
            p = pyaudio.PyAudio()
            # Find default WASAPI loopback device
            wasapi_info = None
            for i in range(p.get_host_api_count()):
                info = p.get_host_api_info_by_index(i)
                if info.get("name", "").lower().find("wasapi") >= 0:
                    wasapi_info = info
                    break

            if not wasapi_info:
                p.terminate()
                logger.debug("No WASAPI host API found")
                return False

            # Get default output device and find its loopback
            default_output = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            loopback_device = None

            for i in range(p.get_device_count()):
                dev = p.get_device_info_by_index(i)
                # pyaudiowpatch marks loopback devices with isLoopbackDevice
                if dev.get("isLoopbackDevice") and dev.get("name", "").startswith(
                    default_output.get("name", "???")
                ):
                    loopback_device = dev
                    break

            if not loopback_device:
                # Fallback: try any loopback device
                for i in range(p.get_device_count()):
                    dev = p.get_device_info_by_index(i)
                    if dev.get("isLoopbackDevice"):
                        loopback_device = dev
                        break

            if not loopback_device:
                p.terminate()
                logger.debug("No WASAPI loopback device found")
                return False

            device_index = loopback_device["index"]
            device_channels = int(loopback_device.get("maxInputChannels", 2))
            device_rate = int(loopback_device.get("defaultSampleRate", 44100))

            logger.info(
                f"WASAPI loopback device: {loopback_device.get('name')} "
                f"(index={device_index}, ch={device_channels}, rate={device_rate}Hz)"
            )
            p.terminate()

            self._thread = threading.Thread(
                target=self._pyaudiowpatch_loop,
                args=(device_index, device_channels, device_rate),
                daemon=True,
            )
            self._thread.start()
            return True

        except Exception as e:
            logger.debug(f"pyaudiowpatch init failed: {e}")
            return False

    def _pyaudiowpatch_loop(self, device_index: int, device_channels: int, device_rate: int):
        try:
            import pyaudiowpatch as pyaudio

            p = pyaudio.PyAudio()
            frames_per_buffer = int(device_rate * 0.1)  # 100ms

            stream = p.open(
                format=pyaudio.paFloat32,
                channels=device_channels,
                rate=device_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=frames_per_buffer,
            )

            while self._running:
                try:
                    data = stream.read(frames_per_buffer, exception_on_overflow=False)
                    audio = np.frombuffer(data, dtype=np.float32)

                    # Convert to mono if needed
                    if device_channels > 1:
                        audio = audio.reshape(-1, device_channels).mean(axis=1)

                    # Resample to target rate if needed
                    if device_rate != self.sample_rate:
                        audio = self._resample(audio, device_rate, self.sample_rate)

                    if self.callback:
                        self.callback(audio)

                except IOError:
                    continue
                except Exception as e:
                    logger.error(f"WASAPI capture read error: {e}")
                    break

            stream.stop_stream()
            stream.close()
            p.terminate()

        except Exception as e:
            logger.error(f"WASAPI loopback capture error: {e}")

    # ── Strategy 2: sounddevice WASAPI loopback ──────────────────

    def _try_sounddevice_wasapi(self) -> bool:
        try:
            import sounddevice as sd
        except ImportError:
            return False

        try:
            # Find WASAPI host API
            hostapis = sd.query_hostapis()
            wasapi_idx = None
            for i, api in enumerate(hostapis):
                if "wasapi" in api["name"].lower():
                    wasapi_idx = i
                    break

            if wasapi_idx is None:
                return False

            # Find a loopback device — sounddevice names loopback devices
            # with "Loopback" or matches output device name as input
            devices = sd.query_devices()
            wasapi_api = hostapis[wasapi_idx]
            default_output_idx = wasapi_api.get("default_output_device", -1)

            if default_output_idx < 0:
                return False

            default_output = devices[default_output_idx]
            output_name = default_output["name"]

            # Look for matching loopback input device
            loopback_idx = None
            for i, dev in enumerate(devices):
                if dev["hostapi"] == wasapi_idx and dev["max_input_channels"] > 0:
                    if "loopback" in dev["name"].lower() or output_name in dev["name"]:
                        loopback_idx = i
                        break

            if loopback_idx is None:
                logger.debug("No sounddevice WASAPI loopback found")
                return False

            loopback_dev = devices[loopback_idx]
            dev_channels = min(int(loopback_dev["max_input_channels"]), 2)
            dev_rate = int(loopback_dev["default_samplerate"])

            logger.info(
                f"sounddevice WASAPI loopback: {loopback_dev['name']} "
                f"(index={loopback_idx}, ch={dev_channels}, rate={dev_rate}Hz)"
            )

            self._thread = threading.Thread(
                target=self._sounddevice_loop,
                args=(loopback_idx, dev_channels, dev_rate),
                daemon=True,
            )
            self._thread.start()
            return True

        except Exception as e:
            logger.debug(f"sounddevice WASAPI init failed: {e}")
            return False

    def _sounddevice_loop(self, device_idx: int, dev_channels: int, dev_rate: int):
        try:
            import sounddevice as sd

            def audio_callback(indata, frames, time_info, status):
                if not self._running or not self.callback:
                    return
                audio = indata[:, 0].copy() if indata.ndim > 1 else indata.copy().flatten()
                # Resample if needed
                if dev_rate != self.sample_rate:
                    audio = self._resample(audio, dev_rate, self.sample_rate)
                self.callback(audio.astype(np.float32))

            with sd.InputStream(
                device=device_idx,
                samplerate=dev_rate,
                channels=dev_channels,
                blocksize=int(dev_rate * 0.1),
                dtype="float32",
                callback=audio_callback,
            ):
                while self._running:
                    sd.sleep(100)

        except Exception as e:
            logger.error(f"sounddevice WASAPI capture error: {e}")

    # ── Resampling ───────────────────────────────────────────────

    @staticmethod
    def _resample(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
        if src_rate == dst_rate:
            return audio
        from scipy.signal import resample
        num_samples = int(len(audio) * dst_rate / src_rate)
        return resample(audio, num_samples).astype(np.float32)
