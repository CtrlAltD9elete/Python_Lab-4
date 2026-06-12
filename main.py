from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette import status

from app.api import router as api_router
from app.config import settings
from app.database import database


@asynccontextmanager
async def lifespan(_: FastAPI):
    await database.connect()
    yield
    await database.close()


app = FastAPI(
    title=settings.app_name,
    description="REST API для визначення геолокації IP-адрес із авторизацією користувачів.",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(api_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Дані запиту не пройшли валідацію.",
            "errors": [_serialize_validation_error(error) for error in exc.errors()],
        },
    )


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse("templates/index.html")


def _serialize_validation_error(error: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(error)
    context = serialized.get("ctx")
    if isinstance(context, dict):
        serialized["ctx"] = {key: str(value) for key, value in context.items()}
    return serialized
