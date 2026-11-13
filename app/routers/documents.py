from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Chunk, Document, User
from app.schemas import DocumentOut
from app.services.chunker import chunk_pages
from app.services.extract import ExtractionError, detect_kind, extract_pages

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_out(doc: Document, chunk_count: int) -> DocumentOut:
    out = DocumentOut.model_validate(doc)
    out.chunk_count = chunk_count
    return out


def _get_owned(db: Session, user: User, document_id: int) -> Document:
    doc = db.get(Document, document_id)
    if doc is None or doc.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return doc


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentOut:
    settings = get_settings()
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File is larger than {settings.max_upload_mb} MB",
        )
    filename = file.filename or "document"
    try:
        kind = detect_kind(filename, file.content_type)
        pages = extract_pages(data, kind)
    except ExtractionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    pieces = chunk_pages(pages, settings.chunk_size_words, settings.chunk_overlap_words)
    doc = Document(
        owner_id=user.id,
        filename=filename,
        content_type=file.content_type or kind,
        pages=len(pages),
        word_count=sum(len(p.split()) for p in pages),
        chunks=[Chunk(position=i, page=c.page, text=c.text) for i, c in enumerate(pieces)],
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _to_out(doc, len(pieces))


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[DocumentOut]:
    rows = db.execute(
        select(Document, func.count(Chunk.id))
        .outerjoin(Chunk)
        .where(Document.owner_id == user.id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    ).all()
    return [_to_out(doc, count) for doc, count in rows]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DocumentOut:
    doc = _get_owned(db, user, document_id)
    return _to_out(doc, len(doc.chunks))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    doc = _get_owned(db, user, document_id)
    db.delete(doc)
    db.commit()
