# backend/app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from fastapi import UploadFile
from datetime import datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class InterviewCreateForm(BaseModel):
    company: str
    role: str
    # resume_file은 별도 파라미터로 처리


class QuestionOut(BaseModel):
    id: int
    index_num: int
    text: str
    audio_url: Optional[str] = None
    is_followup: bool = False
    class Config:
        from_attributes = True


class InterviewOut(BaseModel):
    id: int
    company: str
    role: str
    resume_file_url: Optional[str] = None
    status: str
    created_at: datetime  # 이 필드 추가
    questions: List[QuestionOut] = []
    class Config:
        from_attributes = True



class AnswerCreate(BaseModel):
    interview_id: int
    question_id: int
    answer_text: str


class FollowupOut(BaseModel):
    question: QuestionOut
