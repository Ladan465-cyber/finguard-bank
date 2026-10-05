from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.database import Base, engine
from app import models  # noqa: F401 -- ensures models are registered before create_all
from app.routers import auth_router, account_router, transaction_router, admin_router, beneficiary_router

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
app.include_router(beneficiary_router.router)


@app.on_event("startup")
def on_startup():
    # Creates any tables that don't exist yet. The full schema (with FKs,
    # indexes, and comments) lives in database/schema.sql for reference /
    # manual setup; this keeps `uvicorn app.main:app` runnable out of the box.
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------
# Serve the built React frontend (frontend/dist) from this same service,
# so the whole app lives at one address with no separate frontend host
# and no cross-origin requests at all. This block only activates when
# frontend/dist actually exists (i.e. in a deployment where it was built
# as part of the Render build command) -- running the backend alone
# locally with `uvicorn app.main:app --reload` is unaffected.
# ---------------------------------------------------------------------
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Never let this catch-all swallow an API route or the auto docs --
        # FastAPI matches routes in registration order, so those are
        # already matched before requests reach here, but this is an
        # explicit safety net in case a path slips through.
        if full_path.startswith("api/") or full_path in ("docs", "openapi.json", "redoc"):
            raise HTTPException(status_code=404)

        requested = FRONTEND_DIST / full_path
        if full_path and requested.is_file():
            return FileResponse(requested)

        # Any other path (e.g. /dashboard, /admin/login -- React Router
        # routes) gets index.html, and React Router takes over from there.
        return FileResponse(FRONTEND_DIST / "index.html")

else:
    @app.get("/")
    def root():
        return {
            "service": "FinGuard Bank API",
            "status": "running",
            "docs": "/docs",
            "note": "frontend/dist not found -- running in API-only mode (normal for local development).",
        }
