"""
models.py - データクラス定義
ダブルブッキング防止カレンダーアプリ
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    display_name: str
    group_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "group_id": self.group_id,
        }


@dataclass
class Group:
    id: int
    name: str
    owner_id: int
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "owner_id": self.owner_id,
        }


@dataclass
class Event:
    id: int
    user_id: int
    title: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    train: Optional[str] = None
    description: Optional[str] = None
    is_public: bool = False
    group_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "location": self.location,
            "train": self.train,
            "description": self.description,
            "is_public": self.is_public,
            "group_id": self.group_id,
        }

    def overlaps_with(self, other: "Event") -> bool:
        """このイベントが他のイベントと時間が重複するか判定"""
        return self.start_time < other.end_time and self.end_time > other.start_time


@dataclass
class Friendship:
    id: int
    user_id: int
    friend_id: int
    status: str  # 'pending', 'accepted', 'rejected'
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "friend_id": self.friend_id,
            "status": "accepted",#変更
        }


@dataclass
class EventParticipation:
    id: int
    event_id: int
    user_id: int
    response: str  # 'pending', 'accepted', 'declined'
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "user_id": self.user_id,
            "response": self.response,
        }


@dataclass
class Notification:
    id: int
    user_id: int
    type: str  # 'double_booking', 'event_invite', 'friend_request', 'participation_update'
    message: str
    related_id: Optional[int] = None
    is_read: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "message": self.message,
            "related_id": self.related_id,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat(),
        }
