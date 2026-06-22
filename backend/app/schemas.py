from pydantic import BaseModel, Field


class ChatStreamRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    web_search_mode: bool = False


class Source(BaseModel):
    title: str
    url: str | None = None
    document: str | None = None
    page: int | None = None
    snippet: str | None = None


class SessionSummary(BaseModel):
    session_id: str
    title: str
    updated_at: str


class Message(BaseModel):
    role: str
    content: str
    created_at: str
