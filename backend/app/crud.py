# backend/app/crud.py
from sqlalchemy.orm import Session
from typing import List, Optional

from . import models


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, email: str, hashed_password: str) -> models.User:
    user = models.User(email=email, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_interview(db: Session, user_id: int, company: str, role: str, resume_text: str) -> models.Interview:
    itv = models.Interview(user_id=user_id, company=company, role=role, resume_text=resume_text, status="created")
    db.add(itv)
    db.commit()
    db.refresh(itv)
    return itv

def create_interview_with_file(
    db: Session, 
    user_id: int, 
    company: str, 
    role: str,
    resume_file_path: str,
    resume_file_url: str
) -> models.Interview:
    itv = models.Interview(
        user_id=user_id,
        company=company,
        role=role,
        resume_file_path=resume_file_path,
        resume_file_url=resume_file_url,
        status="created"
    )
    db.add(itv)
    db.commit() 
    db.refresh(itv)
    return itv


def set_interview_status(db: Session, interview_id: int, status: str) -> models.Interview:
    itv = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    itv.status = status
    db.commit()
    db.refresh(itv)
    return itv


def create_question(db: Session, interview_id: int, index_num: int, text: str, is_followup: bool = False, audio_url: str = None) -> models.Question:
    q = models.Question(interview_id=interview_id, index_num=index_num, text=text, is_followup=is_followup, audio_url=audio_url)
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def list_questions(db: Session, interview_id: int) -> List[models.Question]:
    return db.query(models.Question).filter(models.Question.interview_id == interview_id, models.Question.is_followup == False).order_by(models.Question.index_num.asc()).all()


def create_answer(db: Session, question_id: int, user_id: int, text: str) -> models.Answer:
    ans = models.Answer(question_id=question_id, user_id=user_id, text=text)
    db.add(ans)
    db.commit()
    db.refresh(ans)
    return ans
