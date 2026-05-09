import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db

router = APIRouter()


class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    session_token: str
    user_id: str
    email: str


def _hash_password(password: str) -> str:
    # MVP: SHA-256. Upgrade path: replace with bcrypt/argon2.
    return hashlib.sha256(password.encode()).hexdigest()


@router.post("/register", response_model=AuthResponse)
def register(request: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    token = secrets.token_urlsafe(32)
    user = User(
        email=request.email,
        hashed_password=_hash_password(request.password),
        session_token=token,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(session_token=token, user_id=str(user.id), email=user.email)


@router.post("/login", response_model=AuthResponse)
def login(request: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.email == request.email).first()
    if not user or user.hashed_password != _hash_password(request.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = secrets.token_urlsafe(32)
    user.session_token = token
    db.commit()
    return AuthResponse(session_token=token, user_id=str(user.id), email=user.email)


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    current_user.session_token = None
    db.commit()
    return {"message": "logged out"}
