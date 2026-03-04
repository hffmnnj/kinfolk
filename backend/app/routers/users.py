"""Users API router."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.get("/", response_model=APIResponse)
async def list_users(db: Session = Depends(get_db)):
    """List all users."""
    users = db.query(User).all()
    return APIResponse(
        data=[UserResponse.model_validate(u) for u in users],
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/", response_model=APIResponse, status_code=201)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user."""
    db_user = User(**user.model_dump(), id=str(uuid.uuid4()))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return APIResponse(
        data=UserResponse.model_validate(db_user),
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/{user_id}", response_model=APIResponse)
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get a user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return APIResponse(
        data=UserResponse.model_validate(user),
        timestamp=datetime.now(timezone.utc),
    )
