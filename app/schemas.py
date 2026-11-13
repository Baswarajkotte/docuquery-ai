from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str
    pages: int
    word_count: int
    created_at: datetime
    chunk_count: int = 0


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    document_ids: list[int] | None = Field(
        default=None, description="Limit the search to these documents. Defaults to all."
    )
    top_k: int | None = Field(default=None, ge=1, le=10)


class Source(BaseModel):
    document_id: int
    filename: str
    page: int
    score: float
    excerpt: str


class QueryResponse(BaseModel):
    answer: str
    mode: str = Field(description="'llm' when Claude wrote the answer, 'extractive' otherwise")
    sources: list[Source]
    latency_ms: int


class QueryLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    answer: str
    mode: str
    latency_ms: int
    created_at: datetime
