from sqlmodel import SQLModel, Field, Session
import hashlib
from typing import Optional


class User(SQLModel, table=True):
    username: str = Field(primary_key=True)
    password_hash: str
    role: str = "staff"  # "admin" | "staff"
    full_name: Optional[str] = None


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password


def create_default_users(session: Session):
    """Ensure default admin and chef users exist."""
    if not session.get(User, "admin"):
        admin = User(
            username="admin", 
            password_hash=hash_password("wangge2026"), 
            role="admin",
            full_name="管理员"
        )
        session.add(admin)
    
    if not session.get(User, "chef"):
        chef = User(
            username="chef", 
            password_hash=hash_password("chef123"), 
            role="staff",
            full_name="后厨主管"
        )
        session.add(chef)
    
    session.commit()
