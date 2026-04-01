<p align="center">
  <h1 align="center">Voxclar</h1>
  <p align="center"><strong>AI-Powered Real-Time Interview & Meeting Assistant</strong></p>
  <p align="center">
    Real-time captions. Instant AI answers. Invisible to screen share.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-blue" />
  <img src="https://img.shields.io/badge/ASR-Deepgram%20Nova--2-green" />
  <img src="https://img.shields.io/badge/AI-Claude%20%7C%20GPT--4o%20%7C%20DeepSeek-orange" />
  <img src="https://img.shields.io/badge/License-Proprietary-red" />
</p>

---

## What is Voxclar?

Voxclar is a desktop application that listens to your meetings and interviews in real time, transcribes what the other person is saying, detects questions, and generates AI-powered suggested answers — all while remaining **completely invisible** during screen sharing.

Think of it as having a brilliant, silent co-pilot who knows your resume, your prep notes, and your entire interview history.

### Key Features

- **Real-Time Captions** — Deepgram Nova-2 streaming ASR, word-by-word like Zoom, with automatic language detection
- **AI Answer Generation** — Claude, GPT-4o, or DeepSeek generate context-aware answers in real time, streamed to a floating overlay
- **Screen Share Protection** — Content protection API ensures Voxclar is invisible in Zoom, Teams, Meet, and all screen sharing tools
- **Smart Context Engine** — AI references your resume, prep notes, and past meeting history to generate personalized answers
- **Echo-Cancelled Dual Audio** — Captures system audio (the other person) and microphone (you) independently with AEC
- **Progressive Memory** — After each meeting, Voxclar summarizes the session and learns your communication patterns over time
- **Multi-Language** — English, Chinese, Japanese, and auto-detect
- **Document Intelligence** — Upload PDFs, DOCX, PPTX — AI reads, understands, and condenses them (not truncation)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Electron Desktop App                │
│  React 19 + Tailwind + Zustand                      │
│  ┌──────────────┐  ┌───────────────────────────┐    │
│  │  Main Window  │  │  Floating Caption Overlay │    │
│  │  (Dashboard,  │  │  (Always-on-top, transparent, │
│  │   Meeting,    │  │   screen-share protected)  │   │
│  │   Profile...) │  └───────────────────────────┘    │
│  └──────┬───────┘                                    │
└─────────┼────────────────────────────────────────────┘
          │ WebSocket
┌─────────▼────────────────────────────────────────────┐
│              Python Local Engine                      │
│                                                       │
│  System Audio ──→ Deepgram Stream ──→ Question Detect │
│       │                                    │          │
│       └── AEC Reference                    ▼          │
│                               AI Answer Generator     │
│  Microphone ──→ AEC ──→ Deepgram ──→ Meeting Record  │
│                                                       │
│  Context: Profile + Prep + Memory + Q&A History       │
└───────────────────────────────────────────────────────┘
          │ HTTPS
┌─────────▼────────────────────────────────────────────┐
│              FastAPI Cloud Backend                     │
│  Auth (JWT) │ Meetings │ Payments │ LLM Proxy         │
│  PostgreSQL │ Redis    │ MinIO    │ pgvector           │
└───────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Desktop | Electron 33, React 19, Vite 6, Tailwind CSS, Zustand |
| Local Engine | Python 3.11, Deepgram Nova-2, faster-whisper (fallback) |
| AI Models | Claude Sonnet 4, GPT-4o-mini, DeepSeek Chat |
| Audio | ScreenCaptureKit (macOS), WASAPI (Windows), AEC |
| Backend | FastAPI, PostgreSQL, Redis, MinIO, Alembic |
| Protocols | WebSocket (engine), REST (backend), SSE (LLM streaming) |

---

## Project Structure

```
Voxclar/
├── packages/
│   ├── desktop/          # Electron + React frontend
│   │   ├── electron/     # Main process + preload
│   │   └── src/          # React components, pages, hooks, stores
│   ├── local-engine/     # Python audio + ASR + AI engine
│   │   └── src/
│   │       ├── audio/    # System capture, mic, AEC, VAD, noise reduction
│   │       ├── asr/      # Deepgram streaming, local Whisper fallback
│   │       ├── ai/       # Question detection, answer generation, context, memory
│   │       └── routing/  # Adaptive hardware benchmarking
│   ├── server/           # FastAPI backend
│   │   └── src/
│   │       ├── api/      # REST endpoints
│   │       ├── models/   # SQLAlchemy ORM
│   │       ├── services/ # Business logic
│   │       └── core/     # Security, config
│   └── shared/           # Protocol definitions (Python + TypeScript)
├── deploy/               # Docker Compose + Nginx
├── scripts/              # Development setup
└── Makefile              # Unified commands
```

---

## Quick Start

### Prerequisites

- macOS 13+ or Windows 10+
- Node.js 18+, Python 3.11+
- API keys: Deepgram, OpenAI or Claude or DeepSeek

### Setup

```bash
# Clone
git clone https://github.com/aiemi/Voxclar.git
cd Voxclar

# Install dependencies
cd packages/desktop && npm install
cd ../local-engine && pip install -e .

# Configure API keys
cp .env.example .env
# Edit .env with your API keys

# Run
cd packages/desktop && npm run electron:dev
```

### API Keys Required

| Service | Purpose | Get it at |
|---------|---------|-----------|
| Deepgram | Real-time speech-to-text | [console.deepgram.com](https://console.deepgram.com) |
| OpenAI | AI answer generation | [platform.openai.com](https://platform.openai.com) |
| Claude | Behavioral/technical answers | [console.anthropic.com](https://console.anthropic.com) |
| DeepSeek | Budget-friendly alternative | [platform.deepseek.com](https://platform.deepseek.com) |

---

## How It Works

### During a Meeting

1. **Start Meeting** — Select meeting type, language, upload prep materials
2. **Real-Time Captions** — System audio streams to Deepgram, captions appear word-by-word
3. **Question Detection** — Rule-based detector identifies questions (zero API cost)
4. **AI Answer** — Question + your profile + prep notes + meeting history → Claude/GPT → streamed to floating overlay
5. **Screen Safe** — Overlay is invisible to Zoom/Teams screen sharing

### After a Meeting

6. **Auto-Summary** — AI condenses the meeting: key Q&A, your response patterns
7. **Memory Update** — Summary stored locally, loaded into next meeting's context
8. **Pattern Learning** — AI builds a progressive understanding of your communication style

---

## Context Management

Voxclar maintains a layered context system:

| Priority | Source | Description |
|----------|--------|-------------|
| Highest | Current Prep Notes | Meeting-specific uploaded documents |
| High | User Profile | Resume, skills, summary (AI-condensed) |
| Medium | Meeting History | Past Q&A highlights, user patterns |
| Low | AI User Insights | Cross-session understanding of the user |
| Live | Current Q&A | This meeting's questions and answers so far |
| Live | User Speech | What the user has said (via mic + AEC) |

All documents are **AI-condensed at upload time** (not truncated), using GPT-4o-mini or DeepSeek for cost efficiency.

---

## Security & Privacy

- **Screen Share Protection**: `setContentProtection(true)` on all windows — content appears black in screen recordings and shares
- **Local-First Audio**: Audio capture and processing happen on-device
- **No Persistent Audio Storage**: Raw audio is never saved to disk
- **API Key Isolation**: All keys stored in `.env`, never bundled with the app
- **Context Isolation**: Electron context bridge with `nodeIntegration: false`

---

## Subscription Plans

| Plan | Price | Minutes | AI Model | Features |
|------|-------|---------|----------|----------|
| Free | $0 | 10 min/mo | Basic | Real-time captions |
| Basic | $9.99/mo | 60 min | GPT-4o-mini | + TXT export |
| Standard | $19.99/mo | 200 min | Claude | + PDF export, resume matching |
| Pro | $49.99/mo | Unlimited | All models | + Custom prompts, API access |

---

## Development

```bash
# Run all services
make dev

# Run individually
make desktop    # Electron + React
make engine     # Python local engine
make server     # FastAPI backend

# Database
make db-migrate
make db-reset

# Tests
make test
```

---

## Roadmap

- [ ] Windows WASAPI loopback audio capture
- [ ] Cloud-synced user memory (cross-device)
- [ ] Custom AI prompt templates
- [ ] Meeting recording & playback
- [ ] Team collaboration features
- [ ] Browser extension version

---

<p align="center">
  Built with Electron, React, Deepgram, and Claude/GPT.<br/>
  <strong>Voxclar</strong> — Your invisible interview advantage.
</p>
