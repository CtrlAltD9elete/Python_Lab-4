from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.database import database, serialize_user
from app.dependencies import get_current_user
from app.geolocation import get_ip_geolocation
from app.schemas import (
    GeolocationResponse,
    HistoryItem,
    IPLookupRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserPublic,
)
from app.security import create_access_token, verify_password


router = APIRouter(prefix="/api")


@router.get("/health", tags=["system"])
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "mongodb": database.ready,
        "mongodb_error": database.error,
    }


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
async def register(user: UserCreate) -> TokenResponse:
    created_user = await database.create_user(user)
    return _token_response(created_user)


@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(payload: UserLogin) -> TokenResponse:
    user = await database.get_user_by_login(payload.login)
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильний логін або пароль.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _token_response(user)


@router.post("/auth/token", response_model=TokenResponse, tags=["auth"])
async def login_for_docs(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    user = await database.get_user_by_login(form.username)
    if user is None or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильний логін або пароль.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _token_response(user)


@router.get("/me", response_model=UserPublic, tags=["auth"])
async def me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return serialize_user(current_user)


@router.post("/geoip", response_model=GeolocationResponse, tags=["geoip"])
async def lookup_ip(
    payload: IPLookupRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> GeolocationResponse:
    geolocation = await get_ip_geolocation(payload.ip_address)
    await database.save_lookup(current_user, geolocation.ip_address, geolocation)
    return geolocation


@router.get("/history", response_model=list[HistoryItem], tags=["geoip"])
async def history(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    return await database.get_history(current_user)


def _token_response(user: dict[str, Any]) -> TokenResponse:
    public_user = UserPublic(**serialize_user(user))
    return TokenResponse(
        access_token=create_access_token(public_user.id, public_user.username),
        user=public_user,
    )
