from datetime import datetime
from sqlmodel import SQLModel, Field


class MenuConversation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    menu_id: str = Field(default="", foreign_key="menu.id", index=True)
    role: str = ""          # "user" | "assistant"
    content: str = ""       # message text
    msg_type: str = ""      # "ask" | "suggest" | "confirm" | "" (for user messages)
    action_data: str = ""   # JSON: for "suggest", stores {remove: [...], add: [...]}
    created_at: datetime = Field(default_factory=datetime.now)
