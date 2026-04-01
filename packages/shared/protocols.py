"""Shared protocol types between server and local-engine."""
from enum import Enum
from dataclasses import dataclass, field


class EngineMessageType(str, Enum):
    TRANSCRIPTION = "transcription"
    QUESTION_DETECTED = "question_detected"
    ANSWER = "answer"
    ENGINE_STATUS = "engine_status"
    ERROR = "error"
    START_MEETING = "start_meeting"
    STOP_MEETING = "stop_meeting"
    UPDATE_SETTINGS = "update_settings"
    PING = "ping"
    PONG = "pong"


class MeetingType(str, Enum):
    GENERAL = "general"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    COFFEE_CHAT = "coffee_chat"
    PROJECT_KICKOFF = "project_kickoff"
    WEEKLY_STANDUP = "weekly_standup"


class QuestionType(str, Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    GENERAL = "general"


class Speaker(str, Enum):
    USER = "user"
    OTHER = "other"
    SYSTEM = "system"


class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    STANDARD = "standard"
    PRO = "pro"


class EngineStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class MeetingConfig:
    meeting_type: MeetingType = MeetingType.GENERAL
    language: str = "en"
    audio_source: str = "system"
    title: str = ""
    prep_notes: str = ""


@dataclass
class TranscriptionMessage:
    type: str = EngineMessageType.TRANSCRIPTION
    text: str = ""
    is_final: bool = False
    speaker: str = Speaker.OTHER
    language: str = "en"
    timestamp_ms: int = 0
    confidence: float = 0.0


@dataclass
class QuestionDetectedMessage:
    type: str = EngineMessageType.QUESTION_DETECTED
    question: str = ""
    question_type: str = QuestionType.GENERAL
    confidence: float = 0.0


@dataclass
class AnswerMessage:
    type: str = EngineMessageType.ANSWER
    token: str = ""


@dataclass
class EngineStatusMessage:
    type: str = EngineMessageType.ENGINE_STATUS
    status: str = EngineStatus.DISCONNECTED
    details: dict = field(default_factory=dict)
