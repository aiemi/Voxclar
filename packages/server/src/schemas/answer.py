from pydantic import BaseModel


class AnswerRequest(BaseModel):
    question: str
    question_type: str = "general"
    meeting_id: str | None = None
    meeting_type: str = "general"
    language: str = "en"
    context: dict | None = None


class SummarizeRequest(BaseModel):
    meeting_id: str
    language: str = "en"


class DocumentAnalyzeRequest(BaseModel):
    document_url: str
    analysis_type: str = "general"


class ExperienceSearchRequest(BaseModel):
    query: str
    top_k: int = 5
