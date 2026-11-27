"""FastAPI application entrypoint for Mini-DIOS Plastics."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.neon_services import load_neon_env

load_neon_env()
load_dotenv()

from api.routes import router

app = FastAPI(
    title="Mini-DIOS Plastics API",
    description="Deterministic Google OR-Tools CP-SAT Plastic Manufacturing Decision Intelligence OS (Egypt & KSA)",
    version="2.1.0",
)

origins_env = os.environ.get("ALLOWED_ORIGINS") or os.environ.get(
    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
)
allow_origins = [o.strip() for o in origins_env.split(",") if o.strip()] or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
allow_credentials = "*" not in allow_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"service": "Mini-DIOS Plastics", "docs": "/docs", "health": "/api/health"}
