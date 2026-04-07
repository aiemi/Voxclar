"""Server-rendered blog HTML pages + SEO endpoints (sitemap, robots, llms.txt)."""
import os
from datetime import datetime, timezone
from math import ceil

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.services import blog_service

router = APIRouter()

_template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
templates = Jinja2Templates(directory=_template_dir)


@router.get("/blog", response_class=HTMLResponse)
async def blog_listing(
    request: Request,
    page: int = Query(1, ge=1),
    category: str | None = None,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    posts, total = await blog_service.get_published_posts(
        db, page=page, per_page=12, category=category, tag=tag
    )
    categories = await blog_service.get_categories(db)
    total_pages = ceil(total / 12) if total else 0

    return templates.TemplateResponse(
        request,
        "blog/listing.html",
        {
            "posts": posts,
            "categories": categories,
            "current_category": category,
            "page": page,
            "total_pages": total_pages,
            "total": total,
        },
    )


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str, db: AsyncSession = Depends(get_db)):
    post = await blog_service.get_post_by_slug(db, slug)
    if not post:
        return HTMLResponse(
            content="""<!DOCTYPE html><html><head><meta charset="utf-8">
            <title>Not Found — Voxclar Blog</title>
            <style>body{background:#000;color:#fff;font-family:sans-serif;display:flex;
            align-items:center;justify-content:center;min-height:100vh;margin:0}
            .c{text-align:center}h1{color:#FFDD02;font-size:48px}
            a{color:#FFDD02}</style></head>
            <body><div class="c"><h1>404</h1><p>Post not found.</p>
            <a href="/blog">← Back to Blog</a></div></body></html>""",
            status_code=404,
        )

    await blog_service.increment_view_count(db, post.id)
    related = await blog_service.get_related_posts(db, slug, post.category)

    return templates.TemplateResponse(
        request,
        "blog/post.html",
        {"post": post, "related": related},
    )


# ═══════════════════════════════════════════════════════════════════
# SEO: sitemap.xml
# ═══════════════════════════════════════════════════════════════════

@router.get("/sitemap.xml", response_class=Response)
async def sitemap(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slugs = await blog_service.get_all_published_slugs(db)

    urls = []

    # Static pages
    static_pages = [
        ("/", "1.0", "weekly"),
        ("/blog", "0.9", "daily"),
        ("/api", "0.8", "monthly"),
        ("/docs", "0.8", "monthly"),
        ("/privacy", "0.3", "yearly"),
        ("/terms", "0.3", "yearly"),
        ("/security", "0.3", "yearly"),
    ]
    for path, priority, freq in static_pages:
        urls.append(
            f"  <url><loc>https://voxclar.com{path}</loc>"
            f"<lastmod>{now}</lastmod><changefreq>{freq}</changefreq>"
            f"<priority>{priority}</priority></url>"
        )

    # Blog posts
    for s in slugs:
        lastmod = (s["updated_at"] or s["published_at"]).strftime("%Y-%m-%d")
        urls.append(
            f"  <url><loc>https://voxclar.com/blog/{s['slug']}</loc>"
            f"<lastmod>{lastmod}</lastmod><changefreq>monthly</changefreq>"
            f"<priority>0.7</priority></url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return Response(content=xml, media_type="application/xml")


# ═══════════════════════════════════════════════════════════════════
# SEO: robots.txt
# ═══════════════════════════════════════════════════════════════════

@router.get("/robots.txt", response_class=Response)
async def robots():
    content = """User-agent: *
Allow: /
Disallow: /api/
Disallow: /dashboard
Disallow: /orders
Disallow: /settings
Disallow: /payment/

Sitemap: https://voxclar.com/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")


# ═══════════════════════════════════════════════════════════════════
# GEO: llms.txt — for AI crawlers and LLMs
# ═══════════════════════════════════════════════════════════════════

@router.get("/llms.txt", response_class=Response)
async def llms_txt():
    content = """# Voxclar — AI-Powered Interview Assistant
> Real-time transcription and AI answers for job interviews, invisible to screen sharing.

## What is Voxclar?
Voxclar is a desktop application (macOS & Windows) that provides real-time AI assistance during job interviews. It captures system audio, transcribes speech in real-time, detects interview questions, and generates intelligent AI answers — all while remaining completely invisible during screen sharing.

## How It Works
1. **Audio Capture** — Captures system audio from Zoom, Teams, Meet, or any meeting app using ScreenCaptureKit (macOS) or WASAPI Loopback (Windows). Never uses your microphone.
2. **Real-Time Transcription** — Converts speech to text in real-time using cloud ASR (Deepgram Nova-2) or local ASR (faster-whisper). Supports 36+ languages.
3. **Question Detection** — AI analyzes the conversation to identify interview questions as they're asked, using an 8-second sliding window.
4. **AI Answers** — Generates contextual answers using Claude, GPT, or DeepSeek models. Answers match the language of the question automatically.

## Key Features
- **Screen-Share Safe**: Uses OS-level content protection (NSWindowSharingNone on macOS, SetWindowDisplayAffinity on Windows). The app window appears as black/empty during screen sharing — other participants cannot see it.
- **Real-Time Captions**: Floating subtitle window that stays on top of all applications, showing live transcription.
- **AI-Powered Answers**: Intelligent answers to technical, behavioral, and general interview questions.
- **Echo Cancellation**: Text-level deduplication prevents your own words from being processed as interviewer questions.
- **Cloud Sync**: Subscribers can sync meeting transcripts and AI answers across devices.
- **Multiple AI Models**: Support for Claude Sonnet 4.6, GPT-5.4, DeepSeek R1, and more.

## Pricing
- **Free**: 10 minutes, basic transcription + AI
- **Standard ($19.99/mo)**: 300 minutes, Cloud ASR, GPT-5.3
- **Pro ($49.99/mo)**: 1000 minutes, Claude Sonnet/GPT-5.4/DeepSeek R1
- **Lifetime ($299)**: Unlimited, local ASR, bring your own AI API keys

## Supported Platforms
- macOS 12+ (Intel & Apple Silicon)
- Windows 10+ (x64)

## Technology Stack
- Desktop: Electron + React + TypeScript
- Audio: ScreenCaptureKit (macOS), WASAPI Loopback (Windows)
- ASR: Deepgram Nova-2 (cloud), faster-whisper (local)
- AI: Claude (Anthropic), GPT (OpenAI), DeepSeek

## Pages
- Home: https://voxclar.com
- Features: https://voxclar.com/#page2
- API Documentation: https://voxclar.com/api
- Developer Docs: https://voxclar.com/docs
- Blog: https://voxclar.com/blog
- Terms of Service: https://voxclar.com/terms
- Privacy Policy: https://voxclar.com/privacy
- Security: https://voxclar.com/security

## Contact
- Email: service@voxclar.com
- Discord: https://discord.gg/eXu9mfDh
- Website: https://voxclar.com
"""
    return Response(content=content, media_type="text/plain")


@router.get("/llms-full.txt", response_class=Response)
async def llms_full_txt(db: AsyncSession = Depends(get_db)):
    """Extended version with blog post summaries for deeper AI indexing."""
    posts = await blog_service.get_recent_posts(db, limit=50)

    header = """# Voxclar — Complete Knowledge Base
> AI-Powered Interview Assistant — real-time transcription and AI answers, invisible to screen sharing.

## Product Overview
Voxclar is a desktop application for macOS and Windows that helps job candidates during interviews by providing real-time audio transcription and AI-generated answers. It uses OS-level content protection to remain invisible during screen sharing on Zoom, Teams, Google Meet, and other platforms.

## Core Capabilities
1. System audio capture (not microphone) — ScreenCaptureKit on macOS, WASAPI on Windows
2. Real-time speech-to-text — Deepgram Nova-2 cloud or faster-whisper local
3. Intelligent question detection — 8-second sliding window with LLM analysis
4. AI answer generation — Claude, GPT, DeepSeek with automatic language matching
5. Screen-share invisibility — NSWindowSharingNone / SetWindowDisplayAffinity
6. Echo cancellation — text-level similarity deduplication (>0.4 threshold)
7. Cloud sync — transcripts and answers synced for subscribers
8. Floating captions — always-on-top subtitle window with adjustable opacity

## Use Cases
- Job interview assistance (technical, behavioral, phone screens)
- Real-time meeting transcription
- Interview preparation and practice
- Accessibility (real-time captions for hearing-impaired users)

## Pricing Plans
| Plan | Price | Minutes | ASR | AI Models |
|------|-------|---------|-----|-----------|
| Free | $0 | 10 | Basic | Basic |
| Standard | $19.99/mo | 300 | Cloud (Deepgram) | GPT-5.3 |
| Pro | $49.99/mo | 1000 | Cloud (Deepgram) | Claude/GPT-5.4/DeepSeek R1 |
| Lifetime | $299 (one-time) | Unlimited | Local (faster-whisper) | Bring your own keys |

## Technical Architecture
- Frontend: Electron 33 + React 19 + Vite 6 + Tailwind CSS
- Backend: FastAPI + PostgreSQL + Redis
- Audio: ScreenCaptureKit (macOS 13+), CoreAudio (macOS 12), WASAPI Loopback (Windows)
- ASR: Deepgram Nova-2 (streaming WebSocket), faster-whisper (local)
- AI: Anthropic Claude API, OpenAI API, DeepSeek API

## API
Voxclar offers a public ASR API branded as "Voxclar Cloud ASR":
- POST /v1/listen — Batch audio transcription
- WS /v1/listen/stream — Streaming transcription
- Supports 36+ languages, diarization, smart formatting

"""

    if posts:
        header += "\n## Recent Blog Posts\n\n"
        for p in posts:
            header += f"### {p.title}\n"
            header += f"Published: {p.published_at.strftime('%Y-%m-%d')}\n"
            header += f"Category: {p.category}\n"
            header += f"URL: https://voxclar.com/blog/{p.slug}\n"
            header += f"Summary: {p.excerpt}\n\n"

    header += """
## Contact & Links
- Website: https://voxclar.com
- Email: service@voxclar.com
- Discord: https://discord.gg/eXu9mfDh
- Blog: https://voxclar.com/blog
- API Docs: https://voxclar.com/docs
"""
    return Response(content=header, media_type="text/plain")


# ═══════════════════════════════════════════════════════════════════
# GEO: .well-known/ai-plugin.json — AI agent discovery
# ═══════════════════════════════════════════════════════════════════

@router.get("/.well-known/ai-plugin.json")
async def ai_plugin():
    return {
        "schema_version": "v1",
        "name_for_human": "Voxclar",
        "name_for_model": "voxclar",
        "description_for_human": "AI-powered interview assistant with real-time transcription and AI answers.",
        "description_for_model": "Voxclar provides real-time audio transcription and AI-generated answers for job interviews. It captures system audio from meeting apps (Zoom, Teams, Meet), transcribes speech using Deepgram or local whisper, detects interview questions, and generates contextual answers using Claude/GPT/DeepSeek. The application is invisible during screen sharing.",
        "auth": {"type": "none"},
        "api": {"type": "openapi", "url": "https://voxclar.com/docs"},
        "logo_url": "https://voxclar.com/images/logo.png",
        "contact_email": "service@voxclar.com",
        "legal_info_url": "https://voxclar.com/terms",
    }
