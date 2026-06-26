from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, modules, test_cases, test_runs, users
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="MVP API for registering and running automated test cases.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(modules.router, prefix=settings.api_prefix)
app.include_router(test_cases.router, prefix=settings.api_prefix)
app.include_router(test_runs.router, prefix=settings.api_prefix)
