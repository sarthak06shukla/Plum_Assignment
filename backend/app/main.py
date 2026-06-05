from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api import routes_admin, routes_auth, routes_claims
from backend.app.core.config import get_settings
from backend.app.db.session import Base, engine
from backend.app.models import entities


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    app = FastAPI(
        title="Plum OPD Claim Adjudication API",
        description="AI-assisted document understanding with deterministic OPD claim adjudication.",
        version="1.0.0",
    )
    origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(routes_auth.router)
    app.include_router(routes_claims.router)
    app.include_router(routes_admin.router)
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()


__all__ = ["app", "entities"]
