from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import Base, engine
from app import models  # noqa: F401 -- ensures models are registered before create_all
from app.routers import auth_router, account_router, transaction_router, admin_router

app = FastAPI(
    title="FinGuard Bank API",
    description="Digital banking API with the FinShield real-time fraud detection engine.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(account_router.router)
app.include_router(transaction_router.router)
app.include_router(admin_router.router)


@app.on_event("startup")
def on_startup():
    # Creates any tables that don't exist yet. The full schema (with FKs,
    # indexes, and comments) lives in database/schema.sql for reference /
    # manual setup; this keeps `uvicorn app.main:app` runnable out of the box.
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"service": "FinGuard Bank API", "status": "running", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
