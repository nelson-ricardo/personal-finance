from typing import Optional

from sqlmodel import SQLModel, Field

class EnvelopeBase(SQLModel):
    name: str
    note: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)