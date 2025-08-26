from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing_extensions import Annotated
from pydantic import StringConstraints
import re

Category = Literal["bug", "timetable", "feature", "other"]
PageURL = Literal["/310", "/timetable", "/feedback", "/guide", "/about"]

NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=20)]
MessageStr = Annotated[str, StringConstraints(min_length=5, max_length=2000)]
PHONE_RE = re.compile(r"^010[0-9]{8}$")

class FeedbackCreate(BaseModel):
    category: Category
    message: MessageStr
    anonymous: bool = False

    page_url: Optional[PageURL] = None
    email: Optional[EmailStr] = None
    name: Optional[NameStr] = None
    phone: Optional[str] = None
    privacy_agree: Optional[bool] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return v
        if not PHONE_RE.fullmatch(v):
            raise ValueError("phone must match ^010[0-9]{8}$")
        return v

    @model_validator(mode="after")
    def validate_anonymous_rules(self):
        if self.anonymous:
            # 익명 → 개인정보 무시
            return self
        # 익명이 아닐 경우 필수값 검사
        missing = []
        if not self.name:
            missing.append("name")
        if not self.phone:
            missing.append("phone")
        if self.privacy_agree is not True:
            missing.append("privacy_agree=true")
        if missing:
            raise ValueError(f"missing required fields for non-anonymous: {', '.join(missing)}")
        return self

class FeedbackCreateResult(BaseModel):
    id: str
    created_at: str