"""AI Support Chat — SSE streaming, no auth required (but auth optional for context)."""
from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.config import get_settings
from src.core.security import decode_access_token

router = APIRouter()

SUPPORT_SYSTEM_PROMPT = """You are Voxclar's AI support assistant. You help users with questions about the Voxclar desktop application — an AI-powered interview assistant.

## Product Knowledge

**What Voxclar Does:**
- Desktop app (macOS & Windows) for real-time interview assistance
- Captures system audio from Zoom, Teams, Google Meet (never uses microphone)
- Real-time speech transcription (36+ languages)
- AI-powered answer suggestions for interview questions
- Screen-share invisible — interviewers cannot see the app during screen sharing
- Floating caption window stays on top of all apps

**Pricing Plans:**
- Free: 10 minutes, basic transcription + AI
- Standard ($19.99/mo): 300 minutes, Cloud ASR (Deepgram Nova-2), GPT-5.3
- Pro ($49.99/mo): 1000 minutes, Claude Sonnet/GPT-5.4/DeepSeek R1, priority support
- Lifetime ($299 one-time): Unlimited minutes, local ASR (faster-whisper), bring your own API keys, device-locked
- Time Boost ($9.99): +120 minutes, never expires
- ASR Minutes ($4.99): +120 Cloud ASR minutes with API key

**Common Issues & Solutions:**
1. "No audio captured" → Check system audio permissions. macOS: System Settings > Privacy > Screen Recording. Windows: run as administrator.
2. "Captions not showing" → Make sure a meeting is active. Click the meeting tab and start a session.
3. "AI answers are slow" → Try switching to a faster model in Settings. Cloud ASR is faster than local.
4. "Screen sharing shows the app" → Voxclar uses OS-level content protection. If you see it during your own screen share test, that's normal — OTHER participants cannot see it.
5. "Login issues" → Try logging out and back in. Check your email/password. Use "Forgot Password" if needed.
6. "Subscription not activated" → Check your email for confirmation. Refresh the app (close and reopen). Contact service@voxclar.com if the issue persists.
7. "Minutes not added after purchase" → Minutes are added automatically. Restart the app. If still missing, email service@voxclar.com with your transaction ID.
8. "Local ASR not working" → Local ASR (faster-whisper) requires the model to be downloaded first. Check Settings > ASR Mode.

**Technical Details:**
- macOS audio: ScreenCaptureKit (13+) or CoreAudio Aggregate Device (12)
- Windows audio: WASAPI Loopback (pyaudiowpatch)
- Cloud ASR: Deepgram Nova-2 via WebSocket
- Local ASR: faster-whisper (Whisper model running locally)
- AI Models: Claude (Anthropic), GPT (OpenAI), DeepSeek

**Contact:**
- Email: service@voxclar.com
- Discord: https://discord.gg/eXu9mfDh

## Formatting Rules:
- Use short paragraphs (2-3 sentences max per paragraph)
- Separate different topics with blank lines
- Use **bold** for key terms or important points
- Use numbered lists for step-by-step instructions
- Use bullet lists for feature lists or options
- Keep the overall response under 200 words

## Behavior Rules:
1. Be helpful, concise, and friendly
2. Answer in the same language as the user's message (Chinese → Chinese, English → English)
3. If you genuinely cannot help with something (account-specific issues, refunds, billing disputes), suggest emailing service@voxclar.com
4. Never make up features that don't exist
5. For technical troubleshooting, give clear step-by-step instructions with numbered steps
"""


class SupportMessage(BaseModel):
    message: str
    history: list[dict] | None = None  # [{"role": "user/assistant", "content": "..."}]


@router.post("/chat")
async def support_chat(
    body: SupportMessage,
    authorization: str = Header(None, alias="Authorization"),
):
    settings = get_settings()

    # Build messages
    messages = []
    if body.history:
        for msg in body.history[-10:]:  # Keep last 10 messages for context
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": body.message})

    # Optional: add user context if authenticated
    user_context = ""
    if authorization and authorization.startswith("Bearer "):
        try:
            payload = decode_access_token(authorization[7:])
            user_context = f"\n[User is logged in, user_id: {payload.get('sub', 'unknown')}]"
        except Exception:
            pass

    system = SUPPORT_SYSTEM_PROMPT
    if user_context:
        system += user_context

    # Use OpenAI gpt-4o-mini for cost efficiency (support doesn't need frontier models)
    from openai import AsyncOpenAI

    async def generate():
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system}] + messages,
            max_tokens=500,
            temperature=0.3,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield f"data: {delta.content}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
