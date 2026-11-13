# DocuQuery AI

[![CI](https://github.com/Baswarajkotte/docuquery-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/Baswarajkotte/docuquery-ai/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)

A REST API that lets each user upload their own PDFs and text files and ask questions about them.
Every answer cites the document and page it came from.

It uses **retrieval-augmented generation (RAG)**: the API finds the passages that best match the
question with BM25 ranking, then asks Claude to answer using only those passages. Without an API
key it still works offline and returns the best-matching sentences instead.

## Features

- **JWT authentication**: register, log in, and every document is private to its owner
- **Document ingestion**: PDF, TXT and Markdown; text is extracted page by page and split into overlapping chunks
- **BM25 search**: the same ranking function used by Elasticsearch, written from scratch with no extra service
- **Grounded answers**: Claude answers only from the retrieved passages and cites them as `[1]`, `[2]`
- **Graceful fallback**: if the LLM is missing, rate-limited or declines, the API returns an extractive answer
- **Query history**: each question, answer, mode and latency is logged per user
- **Production setup**: SQLAlchemy 2.0 (SQLite or PostgreSQL), Docker Compose, GitHub Actions CI, 20 pytest tests

## Architecture

```
Client ──JWT──▶ FastAPI
                 │
   POST /documents ─▶ extract text (pypdf) ─▶ chunk (180 words, 40 overlap) ─▶ PostgreSQL
                 │
   POST /query ─────▶ load user's chunks ─▶ BM25 top-k ─▶ Claude (answer + citations)
                                                      └─▶ extractive fallback
```

```
app/
├── main.py            # FastAPI app and router wiring
├── config.py          # settings from environment / .env
├── database.py        # SQLAlchemy engine and session
├── models.py          # User, Document, Chunk, QueryLog
├── schemas.py         # Pydantic request/response models
├── security.py        # bcrypt hashing, JWT create/verify
├── deps.py            # current-user dependency
├── routers/           # auth, documents, query
└── services/
    ├── extract.py     # PDF / text extraction
    ├── chunker.py     # overlapping word windows
    ├── retriever.py   # BM25 ranking
    └── answer.py      # Claude answer + extractive fallback
```

## Run it

**Locally (SQLite):**

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # add ANTHROPIC_API_KEY for LLM answers (optional)
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive Swagger UI.

**With Docker (PostgreSQL):**

```bash
docker compose up --build
```

## Try it

```bash
# 1. Register and log in
curl -X POST localhost:8000/auth/register -H "Content-Type: application/json" \
     -d '{"email":"me@example.com","password":"password123"}'
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
     -d "username=me@example.com&password=password123" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. Upload a document
curl -X POST localhost:8000/documents -H "Authorization: Bearer $TOKEN" -F "file=@handbook.pdf"

# 3. Ask a question
curl -X POST localhost:8000/query -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"question":"How many days of sick leave do employees get?"}'
```

Example response:

```json
{
  "answer": "Employees get 12 days of sick leave per year, and a medical certificate is needed after 2 days [1].",
  "mode": "llm",
  "sources": [
    {"document_id": 1, "filename": "handbook.pdf", "page": 4, "score": 3.912, "excerpt": "Sick leave is 12 days per year..."}
  ],
  "latency_ms": 1840
}
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create an account |
| POST | `/auth/login` | Get a JWT access token (OAuth2 password form) |
| GET | `/auth/me` | Current user |
| POST | `/documents` | Upload a PDF / TXT / MD file (max 10 MB) |
| GET | `/documents` | List your documents with chunk counts |
| GET | `/documents/{id}` | Document details |
| DELETE | `/documents/{id}` | Delete a document and its chunks |
| POST | `/query` | Ask a question, optionally limited to `document_ids` |
| GET | `/history` | Your recent questions and answers |
| GET | `/health` | Health check |

## Tests

```bash
pytest -v
```

Tests cover authentication, per-user data isolation, upload validation, chunking, BM25 ranking,
citation formatting, and the LLM fallback paths (the Claude client is mocked, so tests need no network).

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./docuquery.db` | Any SQLAlchemy URL, e.g. PostgreSQL |
| `JWT_SECRET` | `change-me-in-production` | Secret used to sign tokens |
| `ANTHROPIC_API_KEY` | empty | Enables Claude answers |
| `LLM_MODEL` | `claude-opus-5-5` | Claude model used for answers |
| `MAX_UPLOAD_MB` | `10` | Upload size limit |
| `CHUNK_SIZE_WORDS` / `CHUNK_OVERLAP_WORDS` | `180` / `40` | Chunking window |

## Possible next steps

- Embedding-based (vector) search alongside BM25 for hybrid retrieval
- OCR for scanned PDFs
- Background ingestion with a task queue for large files

## Author

**Kotte Baswaraj**, Python Backend Developer · [LinkedIn](https://linkedin.com/in/kotte-baswaraj)
