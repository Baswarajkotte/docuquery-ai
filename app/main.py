import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.config import get_settings
from app.database import Base, engine
from app.routers import auth, documents, query

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=get_settings().app_name,
    version=__version__,
    description="Upload PDFs or text files and ask questions about them. "
    "Answers cite the exact document and page they came from.",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(query.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "version": __version__}
