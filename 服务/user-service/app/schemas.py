# ============================================
# Lumina 墨光 · Pydantic Schemas
# ============================================
import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, EmailStr, Field


# ─── 通用 ───
class SuccessResponse(BaseModel):
    code: int = 0
    message: str = "success"


# ─── 用户 ───
class UserBase(BaseModel):
    name: str
    email: EmailStr
    student_id: Optional[str] = None
    role: str = "student"
    department: Optional[str] = None
    grade: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="密码至少 8 位")


class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


class UserOut(BaseModel):
    id: uuid.UUID
    student_id: Optional[str]
    name: str
    email: EmailStr
    role: str
    department: Optional[str]
    grade: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── 认证 ───
class LoginRequest(BaseModel):
    username: str = Field(..., description="学号/工号或邮箱")
    password: str
    device: str = Field("web", pattern="^(web|mobile|desktop)$")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


# ─── 埋点 ───
class EventTrackRequest(BaseModel):
    event_name: str
    properties: Optional[dict[str, Any]] = None
    course_id: Optional[uuid.UUID] = None
    page_url: Optional[str] = None


class EventTrackOut(BaseModel):
    event_name: str
    user_id: Optional[uuid.UUID]
    properties: Optional[dict]
    created_at: datetime