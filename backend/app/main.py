import re

from fastapi import FastAPI, Request, Response
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
    origins = [origin.strip().rstrip("/") for origin in settings.cors_origins.split(",") if origin.strip()]
    origin_set = set(origins)
    origin_regex = re.compile(settings.cors_origin_regex) if settings.cors_origin_regex else None

    def is_allowed_origin(origin: str | None) -> bool:
        if not origin:
            return False
        normalized = origin.rstrip("/")
        return normalized in origin_set or bool(origin_regex and origin_regex.fullmatch(normalized))

    def apply_cors_headers(response: Response, origin: str | None) -> Response:
        if not is_allowed_origin(origin):
            return response
        response.headers["Access-Control-Allow-Origin"] = origin.rstrip("/")
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Authorization,Content-Type,Accept,Origin"
        response.headers["Access-Control-Max-Age"] = "600"
        response.headers.add_vary_header("Origin")
        return response

    @app.middleware("http")
    async def production_cors_headers(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method == "OPTIONS" and is_allowed_origin(origin):
            return apply_cors_headers(Response(status_code=204), origin)
        response = await call_next(request)
        return apply_cors_headers(response, origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=settings.cors_origin_regex,
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
