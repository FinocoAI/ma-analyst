from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    sources_cited: list[str] = []


class ChatMessage(BaseModel):
    id: str
    run_id: str
    role: str  # "user" | "assistant"
    content: str
    created_at: str
