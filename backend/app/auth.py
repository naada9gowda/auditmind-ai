"""
auth.py — MVP authentication via X-User-Id header.

A seeded user is looked up by ID on every request. The user's
organisation_id is extracted and attached to every query.

Usage in a router:
    from app.auth import current_user, require_role
    from app.models.user import User

    @router.get("/")
    def my_endpoint(user: User = Depends(current_user)):
        ...

    @router.post("/admin-only")
    def admin_endpoint(user: User = Depends(require_role("admin", "compliance_officer"))):
        ...
"""

from __future__ import annotations

from functools import partial
from typing import Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User


def _get_current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> User:
    """Resolve X-User-Id header to a User ORM object."""
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-Id header is required.",
        )
    user = db.get(User, x_user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User '{x_user_id}' not found.",
        )
    return user


# FastAPI dependency — use as `Depends(current_user)`
current_user = Depends(_get_current_user)


def _require_role_dep(*allowed_roles: str) -> Callable:
    """
    Returns a FastAPI dependency that:
    1. Resolves the current user (via X-User-Id).
    2. Raises 403 if the user's role is not in `allowed_roles`.
    """
    def _dep(user: User = Depends(_get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not authorised for this action. "
                       f"Required: {list(allowed_roles)}.",
            )
        return user
    return _dep


def require_role(*roles: str) -> Depends:
    """
    Helper to protect a route to specific roles.

    Example:
        @router.delete("/{id}")
        def delete(user: User = require_role("admin")):
            ...
    """
    return Depends(_require_role_dep(*roles))
