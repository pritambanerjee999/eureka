"""
FastAPI application factory for the Eureka REST API.

Author: Pritam
Date: 2026-10-12
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)

from routers.auth import router as auth_router
from routers.history import router as history_router
from routers.token import router as token_router

app = FastAPI(title="Eureka API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(token_router)
app.include_router(history_router)


@app.get("/health")
async def health() -> dict:
    """Return a simple liveness probe response.

    Returns:
        A dict with a single ``status`` key set to ``"ok"``.
    """
    return {"status": "ok"}
