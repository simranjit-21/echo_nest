# app/models.py
from datetime import date, datetime
from typing import List, Optional

from flask_login import UserMixin
from sqlmodel import Field, Relationship, SQLModel


class User(UserMixin, SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    entries: List["Entry"] = Relationship(back_populates="user")
    habit_events: List["HabitEvent"] = Relationship(back_populates="user")


class Entry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entry_date: date = Field(default_factory=date.today)
    mood: int = Field(ge=1, le=5)  # emotional intensity on a 1-5 scale
    emotion_state: str = Field(default="calm", index=True)
    activities: Optional[str] = None  # CSV list (free-form)
    sleep_hours: Optional[float] = Field(default=None, ge=0, le=24)
    interaction_level: Optional[int] = Field(default=None, ge=1, le=5)
    screen_time_hours: Optional[float] = Field(default=None, ge=0, le=24)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="entries")


class HabitEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    occurred_on: date = Field(default_factory=date.today, index=True)
    habit_key: str = Field(index=True)
    habit_title: str
    emotional_state: str = Field(default="calm", index=True)
    points: int = Field(default=10, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="habit_events")
