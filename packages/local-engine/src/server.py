"""WebSocket server for communication with Electron desktop app.

Lifetime version: all AI runs locally. No server dependency.
"""
import asyncio
import json
import logging
import os
from pathlib import Path

import websockets

# Load .env from project root
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

    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
                msg_type = msg.get("type")

                if msg_type == "start_meeting":
                    ENGINE.start_meeting(
                        meeting_type=msg.get("meeting_type", "general"),
                        language=msg.get("language", "en"),
                        audio_source=msg.get("audio_source", "system"),
                        prep_notes=msg.get("prep_notes", ""),
                        profile_context=msg.get("profile_context", ""),
                        prep_docs_summary=msg.get("prep_docs_summary", ""),
                        meeting_title=msg.get("meeting_title", ""),
                        memory_data=msg.get("memory_data", ""),
                        asr_mode=msg.get("asr_mode", "local"),
                        user_api_keys=msg.get("user_api_keys"),
                        ai_model=msg.get("ai_model", "auto"),
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
    """Summarize document using local OpenAI API calls."""
    try:
        from src.ai.document_summarizer import summarize_document
        summary = await summarize_document(text, doc_type)
        logger.info(f"Document summarized: {doc_id} -> {len(summary)} chars")
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
    """Extract text from binary file. Supports PDF, DOCX, TXT."""
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
            return file_bytes.decode('utf-8', errors='ignore')

    except Exception as e:
        logger.error(f"File parsing error ({filename}): {e}")
        return file_bytes.decode('utf-8', errors='ignore')[:3000]


async def extract_and_send_profile(websocket, resume_text: str):
    """Extract structured profile from resume using local OpenAI API."""
    try:
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            await websocket.send(json.dumps({
                "type": "profile_extracted",
                "profile": {},
                "resume_text": resume_text[:3000],
            }))
            return

        use_deepseek = not os.environ.get("OPENAI_API_KEY")
        from openai import AsyncOpenAI

        if use_deepseek:
            client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            model = "deepseek-chat"
        else:
            client = AsyncOpenAI(api_key=api_key)
            model = "gpt-4o-mini"

        extract_prompt = (
            "Extract structured info from this resume/CV. "
            "Return JSON only: "
            '{"name":"full name","headline":"most recent role + company",'
            '"summary":"2-3 sentence professional summary highlighting key achievements",'
            '"skills":["skill1","skill2",...up to 15 most relevant skills]}'
        )

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": extract_prompt},
                {"role": "user", "content": resume_text[:6000]},
            ],
            max_tokens=500,
            temperature=0,
        )

        result_text = response.choices[0].message.content or ""

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
    log_path = os.path.join(os.path.expanduser("~"), "voxclar-engine.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, mode="w"),
        ],
    )
    logger.info(f"Starting Voxclar Lifetime Engine on ws://localhost:9876 (log: {log_path})")

    async with websockets.serve(handle_client, "localhost", 9876):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
