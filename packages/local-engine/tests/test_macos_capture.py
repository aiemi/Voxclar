"""Tests for MacOSCapture — 系统音频捕获，不会 fallback 到麦克风。"""
from unittest.mock import patch, MagicMock

from src.audio.macos_capture import MacOSCapture


class TestMacOSVersion:
    @patch("platform.mac_ver", return_value=("14.3.1", ("", "", ""), ""))
    def test_sck_available_macos_14(self, _):
        assert MacOSCapture._is_screencapturekit_available() is True

    @patch("platform.mac_ver", return_value=("13.0.0", ("", "", ""), ""))
    def test_sck_available_macos_13(self, _):
        assert MacOSCapture._is_screencapturekit_available() is True

    @patch("platform.mac_ver", return_value=("12.7.2", ("", "", ""), ""))
    def test_sck_unavailable_macos_12(self, _):
        assert MacOSCapture._is_screencapturekit_available() is False

    @patch("platform.mac_ver", return_value=("11.6.0", ("", "", ""), ""))
    def test_sck_unavailable_macos_11(self, _):
        assert MacOSCapture._is_screencapturekit_available() is False


class TestDiagnose:
    @patch("platform.mac_ver", return_value=("14.3.1", ("", "", ""), ""))
    def test_macos_14_can_capture(self, _):
        r = MacOSCapture.diagnose()
        assert r["can_capture_system_audio"] is True
        assert r["recommended_method"] == "screencapturekit"

    @patch("platform.mac_ver", return_value=("12.7.0", ("", "", ""), ""))
    def test_macos_12_needs_pyobjc(self, _):
        r = MacOSCapture.diagnose()
        assert r["recommended_method"] == "aggregate_device"
        # pyobjc 可能不装，此时 can_capture = False
        assert isinstance(r["can_capture_system_audio"], bool)

    @patch("platform.mac_ver", return_value=("11.0.0", ("", "", ""), ""))
    def test_macos_11_cannot_capture(self, _):
        r = MacOSCapture.diagnose()
        assert r["can_capture_system_audio"] is False
        assert any("NOT supported" in n for n in r["notes"])


class TestFallbackStrategy:
    """验证核心原则：绝不 fallback 到麦克风作为系统音频。"""

    @patch.object(MacOSCapture, "_is_screencapturekit_available", return_value=True)
    @patch.object(MacOSCapture, "_compile_swift_helper", return_value="/tmp/fake")
    @patch("threading.Thread")
    def test_uses_sck_when_available(self, mock_thread, *_):
        cap = MacOSCapture()
        cap.start()
        assert cap.method == "screencapturekit"
        cap._running = False

    @patch.object(MacOSCapture, "_is_screencapturekit_available", return_value=False)
    @patch.object(MacOSCapture, "_try_create_aggregate_device", return_value=3)
    @patch("threading.Thread")
    def test_uses_aggregate_when_sck_unavailable(self, mock_thread, *_):
        cap = MacOSCapture()
        cap.start()
        assert cap.method == "aggregate_device"
        cap._running = False

    @patch.object(MacOSCapture, "_is_screencapturekit_available", return_value=False)
    @patch.object(MacOSCapture, "_try_create_aggregate_device", return_value=None)
    def test_unavailable_when_all_fail_NOT_mic(self, *_):
        """核心测试：所有系统音频方案失败时，method='unavailable'，不是 microphone。"""
        cap = MacOSCapture()
        cap.start()
        assert cap.method == "unavailable"
        assert cap._running is False  # 明确停止，不会假装在工作

    @patch.object(MacOSCapture, "_is_screencapturekit_available", return_value=True)
    @patch.object(MacOSCapture, "_compile_swift_helper", return_value=None)
    @patch.object(MacOSCapture, "_try_create_aggregate_device", return_value=None)
    def test_sck_compile_fail_then_unavailable(self, *_):
        """SCK 编译失败 + Aggregate 失败 = unavailable，不是 mic。"""
        cap = MacOSCapture()
        cap.start()
        assert cap.method == "unavailable"
        assert cap._running is False


class TestDualAudioCapture:
    """验证 DualAudioCaptureManager 的双路分离。"""

    def test_system_audio_is_not_mic(self):
        """系统音频和麦克风是两条独立的路。"""
        from src.audio.capture_manager import DualAudioCaptureManager

        mgr = DualAudioCaptureManager()
        # 两路回调是独立的
        assert mgr.on_system_audio is None
        assert mgr.on_mic_audio is None

        # 可以分别设置
        sys_cb = MagicMock()
        mic_cb = MagicMock()
        mgr.on_system_audio = sys_cb
        mgr.on_mic_audio = mic_cb
        assert mgr.on_system_audio is not mgr.on_mic_audio

    def test_system_audio_unavailable_flag(self):
        """系统音频不可用时有明确标志。"""
        from src.audio.capture_manager import DualAudioCaptureManager

        mgr = DualAudioCaptureManager()
        assert mgr.system_audio_available is False  # 未启动
        assert mgr.system_capture_method == "none"
