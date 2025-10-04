"""Health check handlers."""

from fastapi import Response
from fastapi.responses import JSONResponse


async def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(content={"ok": True}, status_code=200)

