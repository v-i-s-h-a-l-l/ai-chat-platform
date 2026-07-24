from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.auth import MessageResponse, UserLogin, UserRegister
from app.services.auth import AuthService
from app.utils.cookies import REFRESH_TOKEN_COOKIE, clear_auth_cookies, set_auth_cookies
from app.utils.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_auth)
def register(request: Request, data: UserRegister, db: Session = Depends(get_db)):
    try:
        AuthService.register_user(db, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return MessageResponse(message="User created successfully")


@router.post("/login", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_auth)
def login(request: Request, data: UserLogin, response: Response, db: Session = Depends(get_db)):
    try:
        user = AuthService.authenticate_user(db, data)
        access_token, refresh_token = AuthService.create_session(db, user)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    set_auth_cookies(response, access_token, refresh_token)
    return MessageResponse(message="Login successful")


@router.post("/refresh", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_auth)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    try:
        access_token, new_refresh_token, _user = AuthService.refresh_session(db, refresh_token)
    except ValueError as exc:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    set_auth_cookies(response, access_token, new_refresh_token)
    return MessageResponse(message="Token refreshed")


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    AuthService.revoke_refresh_token(db, refresh_token)
    clear_auth_cookies(response)
    return MessageResponse(message="Logged out successfully")
