"""Deepgram 实时流式 ASR — 像 Zoom 一样逐词输出。

直连 Deepgram WebSocket API，不走 server 代理。
音频流入 → Deepgram 逐词返回 interim/final → 回调通知 engine。
"""
import asyncio
import json
import logging
import os
from typing import Callable

import numpy as np
import websockets

logger = logging.getLogger(__name__)

DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"


class DeepgramStream:
    """Deepgram 实时流式 ASR 客户端。

    用法：
        stream = DeepgramStream(language="zh", on_transcript=callback)
        await stream.connect()
        # 从音频线程调用：
        stream.send_audio(audio_chunk)  # thread-safe
        # 结束时：
        await stream.disconnect()
    """

    def __init__(
        self,
        language: str = "en",
        on_transcript: Callable[[dict], None] | None = None,
        sample_rate: int = 16000,
    ):
        self.language = language
        self.on_transcript = on_transcript
        self.on_utterance_end: Callable[[], None] | None = None
        self.sample_rate = sample_rate

        self._ws: websockets.WebSocketClientProtocol | None = None
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._send_queue: asyncio.Queue | None = None

        # API key 延迟读取 — connect() 时再检查
        self._api_key = ""

    async def connect(self):
        """连接 Deepgram WebSocket。"""
        self._api_key = os.environ.get("DEEPGRAM_API_KEY", "")
        logger.info(f"DEEPGRAM_API_KEY present: {bool(self._api_key)}, length: {len(self._api_key)}")
        if not self._api_key:
            logger.error("DEEPGRAM_API_KEY not set — Deepgram ASR will not work")
            return False

        self._loop = asyncio.get_running_loop()
        self._send_queue = asyncio.Queue()

        # Deepgram 参数：
        #   model=nova-2 (最新最快)
        #   smart_format=true (自动标点)
        #   interim_results=true (逐词 interim)
        #   utterance_end_ms=1500 (1.5秒静音认为一句话结束)
        #   vad_events=true (VAD 事件)
        #   encoding=linear16, sample_rate=16000, channels=1
        lang_param = self.language if self.language and self.language != "multi" else "multi"
        url = (
            f"{DEEPGRAM_WS_URL}"
            f"?model=nova-2"
            f"&language={lang_param}"
            f"&smart_format=true"
            f"&interim_results=true"
            f"&endpointing=1500"
            f"&vad_events=true"
            f"&diarize=true"
            f"&encoding=linear16"
            f"&sample_rate={self.sample_rate}"
            f"&channels=1"
        )

        try:
            self._ws = await websockets.connect(
                url,
                additional_headers={"Authorization": f"Token {self._api_key}"},
                ping_interval=20,
            )
            self._running = True
            logger.info(f"Deepgram connected (language={self.language})")

            # 启动收发任务
            asyncio.create_task(self._receive_loop())
            asyncio.create_task(self._send_loop())

            return True

        except Exception as e:
            logger.error(f"Deepgram connection failed: {e}")
            return False

    def send_audio(self, audio: np.ndarray):
        """从音频线程发送 audio chunk（thread-safe）。

        float32 → int16 → bytes，放入 asyncio queue。
        """
        if not self._running or not self._loop or not self._send_queue:
            return

        audio_bytes = (audio * 32768).clip(-32768, 32767).astype(np.int16).tobytes()
        self._loop.call_soon_threadsafe(self._send_queue.put_nowait, audio_bytes)

    async def _send_loop(self):
        """从 queue 取音频数据发送到 Deepgram。"""
        try:
            while self._running and self._ws:
                data = await self._send_queue.get()
                if data is None:
                    break
                await self._ws.send(data)
        except Exception as e:
            if self._running:
                logger.error(f"Deepgram send error: {e}")

    async def _receive_loop(self):
        """接收 Deepgram 返回的转写结果。"""
        try:
            async for message in self._ws:
                if not self._running:
                    break

                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "Results":
                    self._handle_result(data)
                elif msg_type == "UtteranceEnd":
                    # Deepgram 判断这个人说完了一段话
                    logger.info("[Deepgram] UtteranceEnd received")
                    if self.on_utterance_end:
                        self.on_utterance_end()
                elif msg_type == "Error":
                    logger.error(f"Deepgram error: {data}")

        except websockets.ConnectionClosed:
            logger.info("Deepgram connection closed")
        except Exception as e:
            if self._running:
                logger.error(f"Deepgram receive error: {e}")
        finally:
            self._running = False

    def _handle_result(self, data: dict):
        """解析 Deepgram Results 消息。"""
        channel = data.get("channel", {})
        alternatives = channel.get("alternatives", [])
        if not alternatives:
            return

        alt = alternatives[0]
        text = alt.get("transcript", "").strip()
        if not text:
            return

        is_final = data.get("is_final", False)
        speech_final = data.get("speech_final", False)
        language = (
            channel.get("detected_language")
            or data.get("metadata", {}).get("detected_language")
            or self.language
        )

        # 提取说话人信息（diarization）
        speaker = None
        words = alt.get("words", [])
        if words:
            # 取第一个词的 speaker（一个 final 通常是同一个人说的）
            speaker = words[0].get("speaker")

        result = {
            "text": text,
            "is_final": is_final or speech_final,
            "language": language or "en",
            "confidence": alt.get("confidence", 0),
            "speaker_id": speaker,  # 0, 1, 2... 或 None
        }

        if self.on_transcript:
            self.on_transcript(result)

    async def disconnect(self):
        """关闭连接。"""
        self._running = False
        if self._send_queue:
            self._send_queue.put_nowait(None)
        if self._ws:
            try:
                # Deepgram 协议：发送 close 消息
                await self._ws.send(json.dumps({"type": "CloseStream"}))
                await self._ws.close()
            except Exception:
                pass
        logger.info("Deepgram disconnected")

    @property
    def is_connected(self) -> bool:
        return self._running and self._ws is not None
