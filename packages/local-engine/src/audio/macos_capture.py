"""macOS 系统音频捕获 — 捕获扬声器输出（对方的声音）。

这是 IMEET.AI 的核心模块。在线上会议中，必须捕获系统音频（扬声器输出）
才能听到对方说什么并检测问题。麦克风捕获的是用户自己的声音，不能替代这个功能。

捕获策略（按优先级）：
  1. ScreenCaptureKit (macOS 13+) — Apple 官方 API，零驱动，直接 16kHz
  2. CoreAudio Aggregate Device (macOS 12) — 编程创建虚拟设备，系统输出路由为输入
  3. 无可用方案 → method='unavailable'，通知上层系统音频不可用

绝不会 fallback 到麦克风 — 麦克风是另一路独立的音频流，
由 mic_capture.py 负责，用于捕获用户自己的声音做上下文补充。
"""
import logging
import os
import platform
import subprocess
import tempfile
import threading
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)

# ── ScreenCaptureKit Swift Helper (macOS 13+) ──────────────────────
_SWIFT_CAPTURE_SOURCE = r'''
import Foundation
import ScreenCaptureKit
import AVFoundation

let sampleRate: Double = 16000
let channelCount: Int = 1

class AudioCapture: NSObject, SCStreamOutput, SCStreamDelegate {
    var stream: SCStream?

    func start() async throws {
        let content = try await SCShareableContent.current
        guard let display = content.displays.first else {
            FileHandle.standardError.write("No display found\n".data(using: .utf8)!)
            exit(1)
        }

        let filter = SCContentFilter(display: display, excludingWindows: [])
        let config = SCStreamConfiguration()
        config.capturesAudio = true
        config.excludesCurrentProcessAudio = false
        config.sampleRate = Int(sampleRate)
        config.channelCount = channelCount
        config.width = 2
        config.height = 2
        config.minimumFrameInterval = CMTime(value: 1, timescale: 1)

        stream = SCStream(filter: filter, configuration: config, delegate: self)
        try stream!.addStreamOutput(self, type: .audio, sampleHandlerQueue: .main)
        try await stream!.startCapture()
    }

    func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer,
                of type: SCStreamOutputType) {
        guard type == .audio else { return }
        guard let blockBuffer = CMSampleBufferGetDataBuffer(sampleBuffer) else { return }

        var length = 0
        var dataPointer: UnsafeMutablePointer<Int8>?
        CMBlockBufferGetDataPointer(blockBuffer, atOffset: 0, lengthAtOffsetOut: nil,
                                    totalLengthOut: &length, dataPointerOut: &dataPointer)
        guard let ptr = dataPointer, length > 0 else { return }

        let data = Data(bytes: ptr, count: length)
        FileHandle.standardOutput.write(data)
    }

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        FileHandle.standardError.write("Stream error: \(error)\n".data(using: .utf8)!)
        exit(1)
    }
}

let capture = AudioCapture()
Task {
    do { try await capture.start() }
    catch {
        FileHandle.standardError.write("Start failed: \(error)\n".data(using: .utf8)!)
        exit(1)
    }
}
RunLoop.main.run()
'''


class MacOSCapture:
    """macOS 系统音频捕获 — 专门捕获扬声器输出（对方的声音）。

    策略:
      1. ScreenCaptureKit (macOS 13+) → 系统音频，零驱动
      2. CoreAudio Aggregate Device (macOS 12) → 系统输出路由为输入
      3. method='unavailable' → 明确告知上层无法捕获系统音频

    不会 fallback 到麦克风。麦克风是独立的音频流。
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1,
                 chunk_duration: float = 0.1, callback: Callable | None = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = int(sample_rate * chunk_duration)
        self.callback = callback
        self._running = False
        self._thread: threading.Thread | None = None
        self._process: subprocess.Popen | None = None
        self._method: str = "unknown"
        self._swift_binary: str | None = None
        self._aggregate_device_id = None

    @property
    def method(self) -> str:
        """当前捕获方式: 'screencapturekit' | 'aggregate_device' | 'unavailable'"""
        return self._method

    def start(self):
        self._running = True

        # ── 层级 1: ScreenCaptureKit (macOS 13+) ──
        if self._is_screencapturekit_available():
            self._swift_binary = self._compile_swift_helper()
            if self._swift_binary:
                self._method = "screencapturekit"
                self._thread = threading.Thread(target=self._sck_capture_loop, daemon=True)
                self._thread.start()
                logger.info(
                    "System audio capture: ScreenCaptureKit (macOS 13+, zero drivers)"
                )
                return

        # ── 层级 2: CoreAudio Aggregate Device (macOS 12) ──
        agg_device_index = self._try_create_aggregate_device()
        if agg_device_index is not None:
            self._method = "aggregate_device"
            self._thread = threading.Thread(
                target=self._aggregate_capture_loop, args=(agg_device_index,), daemon=True
            )
            self._thread.start()
            logger.info("System audio capture: CoreAudio Aggregate Device (macOS 12 compat)")
            return

        # ── 无可用方案 ──
        self._method = "unavailable"
        self._running = False
        logger.error(
            "SYSTEM AUDIO CAPTURE UNAVAILABLE. "
            "Cannot detect questions from the other party in the meeting. "
            "Requirements: macOS 13+ (recommended) or macOS 12 with pyobjc. "
            "Current system: macOS %s",
            platform.mac_ver()[0],
        )

    def stop(self):
        self._running = False
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        if self._thread:
            self._thread.join(timeout=3)
        self._destroy_aggregate_device()

    # ═══════════════════════════════════════════════════════════════════
    # 层级 1: ScreenCaptureKit (macOS 13+)
    # ═══════════════════════════════════════════════════════════════════

    def _sck_capture_loop(self):
        """通过 Swift helper 子进程读取系统音频 raw float32 PCM。"""
        try:
            self._process = subprocess.Popen(
                [self._swift_binary],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )

            bytes_per_sample = 4  # float32
            chunk_bytes = self.chunk_size * bytes_per_sample

            while self._running and self._process.poll() is None:
                raw = self._process.stdout.read(chunk_bytes)
                if not raw:
                    continue
                n_samples = len(raw) // bytes_per_sample
                if n_samples == 0:
                    continue
                audio = np.frombuffer(
                    raw[: n_samples * bytes_per_sample], dtype=np.float32
                ).copy()
                if self.callback:
                    self.callback(audio)

            # 进程异常退出
            if self._running and self._process and self._process.poll() not in (None, 0):
                stderr = self._process.stderr.read().decode(errors="replace").strip()
                logger.error(f"ScreenCaptureKit helper exited: {stderr}")
                # 尝试降级到 Aggregate Device
                self._attempt_aggregate_fallback()

        except Exception as e:
            logger.error(f"ScreenCaptureKit error: {e}")
            if self._running:
                self._attempt_aggregate_fallback()

    def _attempt_aggregate_fallback(self):
        """SCK 运行时失败，尝试降级到 Aggregate Device。不会降到麦克风。"""
        agg = self._try_create_aggregate_device()
        if agg is not None:
            self._method = "aggregate_device"
            logger.info("Fallback: CoreAudio Aggregate Device")
            self._aggregate_capture_loop(agg)
        else:
            self._method = "unavailable"
            self._running = False
            logger.error(
                "System audio capture FAILED after SCK crash. "
                "No fallback available. Question detection will not work."
            )

    # ═══════════════════════════════════════════════════════════════════
    # 层级 2: CoreAudio Aggregate Device (macOS 12)
    # ═══════════════════════════════════════════════════════════════════

    def _try_create_aggregate_device(self) -> int | None:
        """通过 CoreAudio 创建 Aggregate Device，将系统输出映射为输入。

        返回 sounddevice device index，失败返回 None。
        需要 pyobjc-framework-CoreAudio。
        """
        try:
            import objc  # noqa: F401
            from CoreAudio import (
                AudioObjectGetPropertyData,
                kAudioHardwarePropertyDefaultOutputDevice,
                kAudioObjectSystemObject,
                kAudioObjectPropertyScopeGlobal,
                kAudioObjectPropertyElementMain,
                kAudioDevicePropertyDeviceUID,
            )
            from AudioToolbox import AudioHardwareCreateAggregateDevice

            # 获取默认输出设备 ID
            prop_addr = (
                kAudioHardwarePropertyDefaultOutputDevice,
                kAudioObjectPropertyScopeGlobal,
                kAudioObjectPropertyElementMain,
            )
            output_device_id = AudioObjectGetPropertyData(
                kAudioObjectSystemObject, prop_addr, 0, None, 4, None
            )

            # 获取输出设备 UID
            uid_addr = (
                kAudioDevicePropertyDeviceUID,
                kAudioObjectPropertyScopeGlobal,
                kAudioObjectPropertyElementMain,
            )
            output_uid = AudioObjectGetPropertyData(
                output_device_id, uid_addr, 0, None, 256, None
            )

            # 创建 Aggregate Device
            agg_desc = {
                "uid": "com.imeetai.aggregate",
                "name": "IMEET System Capture",
                "sub": [{"uid": output_uid, "input": 1}],
            }
            self._aggregate_device_id = AudioHardwareCreateAggregateDevice(agg_desc)

            if self._aggregate_device_id:
                import sounddevice as sd
                devices = sd.query_devices()
                for i, dev in enumerate(devices):
                    if "IMEET" in dev.get("name", "") and dev["max_input_channels"] > 0:
                        return i

            return None

        except ImportError:
            logger.debug(
                "pyobjc-framework-CoreAudio not available. "
                "Install it for macOS 12 system audio capture: "
                "pip install pyobjc-framework-CoreAudio"
            )
            return None
        except Exception as e:
            logger.debug(f"Aggregate Device creation failed: {e}")
            return None

    def _aggregate_capture_loop(self, device_index: int):
        """通过 sounddevice 从 Aggregate Device 读取系统音频。"""
        try:
            import sounddevice as sd

            def audio_callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"Aggregate audio status: {status}")
                if self._running and self.callback:
                    audio = (
                        indata[:, 0].copy() if indata.ndim > 1 else indata.copy().flatten()
                    )
                    self.callback(audio.astype(np.float32))

            with sd.InputStream(
                device=device_index,
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size,
                dtype="float32",
                callback=audio_callback,
            ):
                while self._running:
                    sd.sleep(100)

        except Exception as e:
            logger.error(f"Aggregate Device capture error: {e}")
            self._method = "unavailable"
            self._running = False

    def _destroy_aggregate_device(self):
        """清理 Aggregate Device。"""
        if self._aggregate_device_id:
            try:
                from AudioToolbox import AudioHardwareDestroyAggregateDevice
                AudioHardwareDestroyAggregateDevice(self._aggregate_device_id)
                logger.debug("Aggregate Device destroyed")
            except Exception:
                pass
            self._aggregate_device_id = None

    # ═══════════════════════════════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def get_macos_version() -> tuple[int, int, int]:
        """返回 macOS 版本号 (major, minor, patch)。"""
        try:
            ver = platform.mac_ver()[0]
            parts = [int(x) for x in ver.split(".")]
            while len(parts) < 3:
                parts.append(0)
            return tuple(parts[:3])
        except Exception:
            return (0, 0, 0)

    @classmethod
    def _is_screencapturekit_available(cls) -> bool:
        """macOS >= 13.0 (Ventura)。"""
        major, _, _ = cls.get_macos_version()
        return major >= 13

    @staticmethod
    def _compile_swift_helper() -> str | None:
        """获取 ScreenCaptureKit Swift helper — 优先用预编译版本（原地运行，不复制到/tmp）。"""
        try:
            import sys

            # 1. 查找预编译的 helper（PyInstaller 打包场景）
            # 直接从 app bundle 内运行，继承 Voxclar.app 的屏幕录制权限
            bundled_paths = [
                os.path.join(os.path.dirname(sys.executable), "imeet_audio_capture"),
            ]
            for bundled in bundled_paths:
                if os.path.exists(bundled) and os.access(bundled, os.X_OK):
                    logger.info(f"Using bundled Swift helper: {bundled}")
                    return bundled

            # 2. 检查 /tmp 是否有之前编译好的（开发模式）
            tmp_dir = tempfile.gettempdir()
            binary_path = os.path.join(tmp_dir, "imeet_audio_capture")
            if os.path.exists(binary_path):
                return binary_path

            # 3. Fallback：运行时编译（需要 Xcode Command Line Tools）
            source_path = os.path.join(tmp_dir, "imeet_audio_capture.swift")
            with open(source_path, "w") as f:
                f.write(_SWIFT_CAPTURE_SOURCE)

            result = subprocess.run(
                [
                    "swiftc", "-O",
                    "-framework", "ScreenCaptureKit",
                    "-framework", "CoreMedia",
                    "-framework", "AVFoundation",
                    source_path, "-o", binary_path,
                ],
                capture_output=True, text=True, timeout=60,
            )

            if result.returncode != 0:
                logger.error(f"Swift compilation failed:\n{result.stderr}")
                return None

            logger.info("ScreenCaptureKit Swift helper compiled")
            return binary_path

        except FileNotFoundError:
            logger.warning("swiftc not found — install Xcode Command Line Tools")
            return None
        except subprocess.TimeoutExpired:
            logger.error("Swift compilation timed out")
            return None
        except Exception as e:
            logger.error(f"Swift compilation error: {e}")
            return None

    @classmethod
    def diagnose(cls) -> dict:
        """诊断当前系统的系统音频捕获能力。"""
        major, minor, patch = cls.get_macos_version()
        ver_str = f"{major}.{minor}.{patch}"

        result = {
            "macos_version": ver_str,
            "screencapturekit_available": major >= 13,
            "can_capture_system_audio": False,
            "recommended_method": "unavailable",
            "notes": [],
        }

        if major >= 13:
            result["can_capture_system_audio"] = True
            result["recommended_method"] = "screencapturekit"
            result["notes"].append(
                "ScreenCaptureKit available — best experience, zero drivers"
            )
            try:
                subprocess.run(["swiftc", "--version"], capture_output=True, timeout=5)
                result["swiftc_available"] = True
            except Exception:
                result["swiftc_available"] = False
                result["notes"].append(
                    "swiftc not found — run: xcode-select --install"
                )
        elif major >= 12:
            result["recommended_method"] = "aggregate_device"
            result["notes"].append(
                "macOS 12: CoreAudio Aggregate Device mode available"
            )
            try:
                import objc  # noqa: F401
                result["pyobjc_available"] = True
                result["can_capture_system_audio"] = True
            except ImportError:
                result["pyobjc_available"] = False
                result["can_capture_system_audio"] = False
                result["notes"].append(
                    "pyobjc not installed — system audio capture DISABLED. "
                    "Install: pip install pyobjc-framework-CoreAudio, "
                    "or upgrade to macOS 13+ (recommended)"
                )
        else:
            result["notes"].append(
                f"macOS {ver_str}: system audio capture NOT supported. "
                "IMEET.AI requires macOS 12+ (13+ recommended). "
                "Please upgrade your operating system."
            )

        return result
