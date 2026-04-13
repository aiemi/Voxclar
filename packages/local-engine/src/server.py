"""WebSocket server for communication with Electron desktop app."""
import asyncio
import json
import logging
import os
from pathlib import Path

import websockets

# 加载 .env（从项目根目录）
_env_path = Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

from src.engine import MeetingEngine  # noqa: E402

logger = logging.getLogger(__name__)

ENGINE: MeetingEngine | None = None


async def handle_client(websocket):
    global ENGINE
    logger.info("Desktop client connected")

    if ENGINE is None:
        ENGINE = MeetingEngine()

    loop = asyncio.get_running_loop()
    ENGINE._loop = loop

    # 注册回调 — Deepgram 回调已在 asyncio 线程，但音频回调在其他线程
    # 统一用 thread-safe 方式
    def make_sender(ws):
        def send(data):
            try:
                msg_type = data.get("type", "unknown") if isinstance(data, dict) else "?"
                logger.info(f"[SENDER] sending to Electron: type={msg_type} data={str(data)[:120]}")
                json_str = json.dumps(data)
                loop.call_soon_threadsafe(asyncio.ensure_future, ws.send(json_str))
                logger.info(f"[SENDER] scheduled send OK ({len(json_str)} bytes)")
            except Exception as e:
                logger.error(f"[SENDER] FAILED to send: {e}")
        return send

    sender = make_sender(websocket)
    ENGINE.on_transcription = sender
    ENGINE.on_question_detected = sender
    ENGINE.on_answer_token = sender
    ENGINE.on_status_change = sender
    ENGINE.on_save_memory = sender

    # Send initial status
    await websocket.send(json.dumps({
        "type": "engine_status",
        "status": "ready",
        "details": {"platform": ENGINE.platform},
    }))

    # Engine needs server URL for profile extraction etc. (set on first message)
    def _ensure_server_config(msg):
        """Extract server config from any message that contains it."""
        url = msg.get("server_api_url", "")
        token = msg.get("server_token", "")
        if url and not ENGINE._server_api_url:
            ENGINE._server_api_url = url
            ENGINE._server_token = token

    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
                msg_type = msg.get("type")

                if msg_type == "set_config":
                    # Frontend sends server URL + token on connect
                    ENGINE._server_api_url = msg.get("server_api_url", "")
                    ENGINE._server_token = msg.get("server_token", "")
                    logger.info(f"Server config set: url={ENGINE._server_api_url}")

                elif msg_type == "start_meeting":
                    _ensure_server_config(msg)
                    ENGINE.start_meeting(
                        meeting_type=msg.get("meeting_type", "general"),
                        language=msg.get("language", "en"),
                        audio_source=msg.get("audio_source", "system"),
                        prep_notes=msg.get("prep_notes", ""),
                        profile_context=msg.get("profile_context", ""),
                        prep_docs_summary=msg.get("prep_docs_summary", ""),
                        meeting_title=msg.get("meeting_title", ""),
                        memory_data=msg.get("memory_data", ""),
                        asr_mode=msg.get("asr_mode", "deepgram"),
                        user_api_keys=msg.get("user_api_keys"),
                        ai_model=msg.get("ai_model", "auto"),
                        server_api_url=msg.get("server_api_url", ""),
                        server_token=msg.get("server_token", ""),
                    )
                    await websocket.send(json.dumps({
                        "type": "engine_status",
                        "status": "running",
                    }))

                elif msg_type == "stop_meeting":
                    ENGINE.stop_meeting()
                    await websocket.send(json.dumps({
                        "type": "engine_status",
                        "status": "ready",
                    }))

                elif msg_type == "parse_file":
                    # 只解析文件 → 返回纯文本，不调 AI
                    file_data = msg.get("file_data", "")
                    filename = msg.get("filename", "file.txt")
                    if file_data:
                        import base64
                        file_bytes = base64.b64decode(file_data)
                        text = parse_file_content(file_bytes, filename)
                        await websocket.send(json.dumps({
                            "type": "file_parsed",
                            "filename": filename,
                            "text": text,
                        }))

                elif msg_type == "extract_profile":
                    # 支持 base64 文件或纯文本
                    file_data = msg.get("file_data", "")
                    filename = msg.get("filename", "resume.txt")
                    resume_text = msg.get("resume_text", "")
                    if file_data:
                        import base64
                        file_bytes = base64.b64decode(file_data)
                        resume_text = parse_file_content(file_bytes, filename)
                    if resume_text:
                        asyncio.ensure_future(
                            extract_and_send_profile(websocket, resume_text)
                        )

                elif msg_type == "summarize_document":
                    file_data = msg.get("file_data", "")
                    filename = msg.get("filename", "document.txt")
                    doc_text = msg.get("text", "")
                    doc_type = msg.get("doc_type", "prep_notes")
                    doc_id = msg.get("doc_id", "")
                    if file_data:
                        import base64
                        file_bytes = base64.b64decode(file_data)
                        doc_text = parse_file_content(file_bytes, filename)
                    if doc_text:
                        asyncio.ensure_future(
                            summarize_and_send(websocket, doc_text, doc_type, doc_id)
                        )

                elif msg_type == "update_settings":
                    ENGINE.update_settings(msg.get("settings", {}))

                elif msg_type == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))

            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON",
                }))

    except websockets.ConnectionClosed:
        logger.info("Desktop client disconnected")
    finally:
        if ENGINE and ENGINE.is_running:
            ENGINE.stop_meeting()


async def summarize_and_send(websocket, text: str, doc_type: str, doc_id: str):
    """通过服务器 AI 浓缩文档。"""
    try:
        import httpx
        server_url = ENGINE._server_api_url if ENGINE else ""
        server_token = ENGINE._server_token if ENGINE else ""
        logger.info(f"Summarizing document: {doc_id} ({len(text)} chars)")

        if not server_url:
            raise ValueError("No server URL")

        headers = {"Authorization": f"Bearer {server_token}"}
        summary = ""
        # No truncation — summarization must cover the full document
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{server_url}/ai/answer",
                json={
                    "question": text,
                    "question_type": "general",
                    "meeting_type": "general",
                    "language": "en",
                    "context": f"Summarize this {doc_type} document concisely. Keep key information from ALL sections and sources.",
                }, headers=headers) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        token = line[6:]
                        if token == "[DONE]":
                            break
                        summary += token

        logger.info(f"Document summarized: {doc_id} → {len(summary)} chars")
        await websocket.send(json.dumps({
            "type": "document_summarized",
            "doc_id": doc_id,
            "summary": summary or text[:2000],
        }))
    except Exception as e:
        logger.error(f"Document summarization failed: {e}")
        await websocket.send(json.dumps({
            "type": "document_summarized",
            "doc_id": doc_id,
            "summary": text[:2000],
        }))


def parse_file_content(file_bytes: bytes, filename: str) -> str:
    """从文件二进制中提取文本。支持 PDF、DOCX、TXT。"""
    name_lower = filename.lower()
    try:
        if name_lower.endswith('.pdf'):
            import io
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n".join(pages)

        elif name_lower.endswith(('.docx', '.doc')):
            # docx 是 zip 格式，提取 XML 中的文本
            import io
            import zipfile
            import re
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                if 'word/document.xml' in z.namelist():
                    xml = z.read('word/document.xml').decode('utf-8', errors='ignore')
                    text = re.sub(r'<[^>]+>', ' ', xml)
                    return re.sub(r'\s+', ' ', text).strip()
            return ""

        elif name_lower.endswith(('.pptx', '.ppt')):
            import io
            import zipfile
            import re
            texts = []
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                for name in sorted(z.namelist()):
                    if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
                        xml = z.read(name).decode('utf-8', errors='ignore')
                        text = re.sub(r'<[^>]+>', ' ', xml)
                        text = re.sub(r'\s+', ' ', text).strip()
                        if text:
                            texts.append(text)
            return "\n\n".join(texts)

        else:
            # TXT 等纯文本
            return file_bytes.decode('utf-8', errors='ignore')

    except Exception as e:
        logger.error(f"File parsing error ({filename}): {e}")
        return file_bytes.decode('utf-8', errors='ignore')[:3000]


async def extract_and_send_profile(websocket, resume_text: str):
    """通过服务器 AI 从简历提取结构化信息。"""
    try:
        import httpx
        server_url = ENGINE._server_api_url if ENGINE else ""
        server_token = ENGINE._server_token if ENGINE else ""

        if not server_url:
            await websocket.send(json.dumps({
                "type": "profile_extracted",
                "profile": {},
                "resume_text": resume_text[:3000],
            }))
            return

        # Use server /ai/answer to extract profile
        extract_prompt = (
            "Extract structured info from this resume/CV. "
            "The input may contain MULTIPLE resumes separated by '=== filename ===' markers — "
            "if so, synthesize the combined career narrative across ALL resumes, using the most "
            "recent/relevant info where they differ. "
            "Return JSON only: "
            '{"name":"full name","headline":"most recent role + company",'
            '"summary":"2-3 sentence professional summary highlighting key achievements across all resumes",'
            '"skills":["skill1","skill2",...up to 15 most relevant skills from all resumes]}'
        )
        headers = {"Authorization": f"Bearer {server_token}"}
        result_text = ""
        # No truncation — AI must see all resumes in full to capture complete career history
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{server_url}/ai/answer",
                json={
                    "question": resume_text,
                    "question_type": "general",
                    "meeting_type": "general",
                    "language": "en",
                    "context": extract_prompt,
                }, headers=headers) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        token = line[6:]
                        if token == "[DONE]":
                            break
                        result_text += token

        import re
        match = re.search(r"\{[\s\S]*\}", result_text)
        profile = json.loads(match.group()) if match else {}

        await websocket.send(json.dumps({
            "type": "profile_extracted",
            "profile": profile,
            "resume_text": resume_text[:3000],
        }))
    except Exception as e:
        logger.error(f"Profile extraction failed: {e}")
        await websocket.send(json.dumps({
            "type": "profile_extracted",
            "profile": {},
            "resume_text": resume_text[:3000],
        }))


async def main():
    # Log to both console and file so we can debug Finder launches
    log_path = os.path.join(os.path.expanduser("~"), "voxclar-engine.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, mode="w"),
        ],
    )
    logger.info(f"Starting IMEET.AI Local Engine on ws://localhost:9876 (log: {log_path})")

    async with websockets.serve(handle_client, "localhost", 9876):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
