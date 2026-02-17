from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from backend.models.user import User, verify_password

from backend.database import get_session
from backend.auth_utils import create_access_token, get_current_user
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=dict)
def login(request: LoginRequest, session: Session = Depends(get_session)):
    user = session.get(User, request.username)
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "token": access_token,  # Keep 'token' key for backward compat with frontend if possible, or update frontend
        "access_token": access_token, 
        "token_type": "bearer",
        "username": user.username,
        "role": user.role
    }

@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "role": current_user.role,
        "full_name": current_user.full_name
    }
