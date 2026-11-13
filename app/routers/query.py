import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Chunk, Document, QueryLog, User
from app.schemas import QueryLogOut, QueryRequest, QueryResponse, Source
from app.services.answer import Passage, answer_question
from app.services.retriever import BM25

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def ask(
    payload: QueryRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> QueryResponse:
    started = time.perf_counter()
    k = payload.top_k or get_settings().top_k

    stmt = (
        select(Chunk, Document.filename)
        .join(Document)
        .where(Document.owner_id == user.id)
    )
    if payload.document_ids:
        stmt = stmt.where(Document.id.in_(payload.document_ids))
    rows = db.execute(stmt).all()

    sources: list[Source] = []
    passages: list[Passage] = []
    if rows:
        index = BM25([chunk.text for chunk, _ in rows])
        for hit in index.top_k(payload.question, k):
            chunk, filename = rows[hit.index]
            sources.append(
                Source(
                    document_id=chunk.document_id,
                    filename=filename,
                    page=chunk.page,
                    score=round(hit.score, 3),
                    excerpt=chunk.text[:300],
                )
            )
            passages.append(Passage(label=f"{filename}, page {chunk.page}", text=chunk.text))

    answer, mode = answer_question(payload.question, passages)
    latency_ms = int((time.perf_counter() - started) * 1000)

    db.add(
        QueryLog(
            user_id=user.id,
            question=payload.question,
            answer=answer,
            mode=mode,
            latency_ms=latency_ms,
        )
    )
    db.commit()
    return QueryResponse(answer=answer, mode=mode, sources=sources, latency_ms=latency_ms)


@router.get("/history", response_model=list[QueryLogOut])
def history(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[QueryLog]:
    return list(
        db.scalars(
            select(QueryLog)
            .where(QueryLog.user_id == user.id)
            .order_by(QueryLog.id.desc())
            .limit(limit)
        )
    )
