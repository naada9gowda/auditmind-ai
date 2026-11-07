"""
api/users.py — /api/me endpoint.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import _get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut], summary="List all users")
def list_users(db: Session = Depends(get_db)) -> list:
    """Returns all users in the database."""
    return db.query(User).all()


@router.get("/me", response_model=UserOut, summary="Return the current authenticated user")
def get_me(user: User = Depends(_get_current_user)) -> UserOut:
    """Returns the user resolved from the X-User-Id header."""
    return user  # type: ignore[return-value]

