"""回声消除 (AEC) — 从麦克风信号中去除扬声器回声。

原理：mic = user_voice + echo(system_audio)
使用频域自适应滤波 (Overlap-Save NLMS)，比时域逐样本快几十倍。
"""
import logging
import threading

import numpy as np
from scipy.fft import rfft, irfft

logger = logging.getLogger(__name__)


class EchoCanceller:
    """频域块处理回声消除器。

    用法：
        aec = EchoCanceller()
        aec.feed_reference(system_audio_chunk)     # 系统音频到达时
        clean = aec.cancel(mic_audio_chunk)         # 麦克风音频到达时
    """

    def __init__(self, block_size: int = 1600, filter_blocks: int = 8,
                 mu: float = 0.3, sample_rate: int = 16000):
        """
        Args:
            block_size: 处理块大小 (1600 = 100ms @16kHz)
            filter_blocks: 滤波器块数 (8 × 100ms = 800ms 回声覆盖)
            mu: 步长因子
        """
        self.block_size = block_size
        self.filter_blocks = filter_blocks
        self.mu = mu
        self.fft_size = 2 * block_size

        # 频域自适应滤波器 (filter_blocks 个 FFT 块)
        self._W = np.zeros((filter_blocks, self.fft_size // 2 + 1), dtype=np.complex64)

        # 参考信号环形缓冲 (频域)
        self._X = np.zeros((filter_blocks, self.fft_size // 2 + 1), dtype=np.complex64)

        # 时域缓冲
        self._ref_buf = np.zeros(block_size, dtype=np.float32)
        self._mic_buf = np.zeros(block_size, dtype=np.float32)
        self._ref_queue: list[np.ndarray] = []
        self._mic_queue: list[np.ndarray] = []

        self._lock = threading.Lock()

    def feed_reference(self, audio: np.ndarray):
        """喂入系统音频块。"""
        with self._lock:
            self._ref_queue.append(audio.astype(np.float32).copy())

    def cancel(self, mic_audio: np.ndarray) -> np.ndarray:
        """消除回声，返回干净的用户声音。"""
        with self._lock:
            self._mic_queue.append(mic_audio.astype(np.float32).copy())

            # 取出对齐的参考块
            ref_data = np.concatenate(self._ref_queue) if self._ref_queue else np.array([], dtype=np.float32)
            mic_data = np.concatenate(self._mic_queue) if self._mic_queue else np.array([], dtype=np.float32)
            self._ref_queue.clear()
            self._mic_queue.clear()

            if len(ref_data) == 0 or len(mic_data) == 0:
                return mic_audio.copy()

            # 对齐长度
            min_len = min(len(ref_data), len(mic_data))
            ref_data = ref_data[:min_len]
            mic_data = mic_data[:min_len]

            # 按 block_size 分块处理
            output_parts = []
            bs = self.block_size

            for start in range(0, min_len - bs + 1, bs):
                ref_block = ref_data[start:start + bs]
                mic_block = mic_data[start:start + bs]
                clean_block = self._process_block(ref_block, mic_block)
                output_parts.append(clean_block)

            if not output_parts:
                return mic_audio.copy()

            result = np.concatenate(output_parts)

            # 补齐长度（如果输入不是 block_size 的整数倍）
            if len(result) < len(mic_audio):
                result = np.concatenate([result, mic_audio[len(result):]])

            return result

    def _process_block(self, ref_block: np.ndarray, mic_block: np.ndarray) -> np.ndarray:
        """处理一个块：频域 NLMS。"""
        # 构造 overlap-save 输入
        ref_frame = np.concatenate([self._ref_buf, ref_block])
        self._ref_buf = ref_block.copy()

        # 参考信号 FFT
        X_new = rfft(ref_frame, n=self.fft_size)

        # 移位参考缓冲
        self._X = np.roll(self._X, 1, axis=0)
        self._X[0] = X_new

        # 估计回声 = sum(W_i * X_i)
        Y = np.sum(self._W * self._X, axis=0)
        y = irfft(Y, n=self.fft_size).real[self.block_size:]  # 取后半段

        # 误差 = 麦克风 - 估计回声
        error = mic_block - y[:self.block_size]

        # 频域误差
        error_frame = np.zeros(self.fft_size, dtype=np.float32)
        error_frame[self.block_size:] = error
        E = rfft(error_frame, n=self.fft_size)

        # 归一化功率
        ref_power = np.real(np.sum(self._X * np.conj(self._X), axis=0)) + 1e-8

        # 更新滤波器
        for i in range(self.filter_blocks):
            self._W[i] += self.mu * E * np.conj(self._X[i]) / ref_power

        return np.clip(error, -1.0, 1.0).astype(np.float32)

    def reset(self):
        """重置。"""
        with self._lock:
            self._W[:] = 0
            self._X[:] = 0
            self._ref_buf[:] = 0
            self._ref_queue.clear()
            self._mic_queue.clear()
