from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db


def get_current_user(
    x_session_token: str = Header(...),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.session_token == x_session_token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user
