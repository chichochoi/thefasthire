# backend/app/routers/interview.py
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import crud, schemas, models
from ..routers.user import get_current_user
from ..services import interview_service, audio_service  # 함수로 import
from ..services.gcs_service import GCSService
from app import crud  # 이 라인이 파일 상단에 있는지 확인

router = APIRouter(tags=["interviews"])

@router.post("", response_model=schemas.InterviewOut)
async def create_interview(
    company: str = Form(...),
    role: str = Form(...),
    resume_file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 디버깅용 로그 추가
    print(f"Received data - company: {company}, role: {role}")
    print(f"File info - filename: {resume_file.filename if resume_file else 'None'}")

    try:
        # 파일 존재 및 파일명 검증 개선
        if not resume_file or not resume_file.filename:
            raise HTTPException(status_code=400, detail="파일이 업로드되지 않았습니다")
        
        if not resume_file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")
        
        # 파일 크기 검증 추가
        content = await resume_file.read()
        await resume_file.seek(0)  # 파일 포인터 리셋
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다")
        
        # GCS에 파일 업로드
        gcs_service = GCSService()
        file_path, file_url = await gcs_service.upload_file(resume_file)
        
        # Interview 생성
        interview = crud.create_interview_with_file(
            db=db, 
            user_id=current_user.id, 
            company=company, 
            role=role,
            resume_file_path=file_path,
            resume_file_url=file_url
        )
        
        # PDF 기반 질문 생성 - 함수 직접 호출
        questions_data = interview_service.generate_questions_from_pdf(
            file_path, company, role
        )
        
        # 질문들을 데이터베이스에 저장
        for i, (index, question_text) in enumerate(questions_data):
            # audio_service 함수 직접 호출
            audio_url = audio_service.synthesize_to_file(
                question_text, 
                filename_hint=f"question-{index}-interview{interview.id}"
            )
            crud.create_question(
                db=db,
                interview_id=interview.id,
                index_num=index,
                text=question_text,
                is_followup=False,
                audio_url=audio_url
            )
        
        # 생성된 면접과 질문들을 다시 조회하여 반환
        db.refresh(interview)
        questions = crud.list_questions(db, interview_id=interview.id)

        # InterviewOut 스키마에 맞게 반환
        return schemas.InterviewOut(
            id=interview.id,
            company=interview.company,
            role=interview.role,
            resume_file_url=file_url,  # 이 필드 추가
            status=interview.status,
            created_at=interview.created_at,  # 추가
            questions=[schemas.QuestionOut(
                id=q.id,
                text=q.text,
                audio_url=q.audio_url,
                index_num=q.index_num,
                is_followup=q.is_followup
            ) for q in questions]
        )
        
    except HTTPException:
        raise  # HTTPException은 그대로 재발생
    except Exception as e:
        # 상세한 에러 정보 출력
        import traceback
        error_details = traceback.format_exc()
        print(f"Detailed error: {error_details}")
        
        # 클라이언트에게는 안전한 메시지만 전달
        raise HTTPException(
            status_code=500, 
            detail="면접 생성 중 오류가 발생했습니다"

        )

@router.get("/{interview_id}", response_model=schemas.InterviewOut)
def get_interview(interview_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    itv = db.query(models.Interview).filter(models.Interview.id == interview_id, models.Interview.user_id == current_user.id).first()
    if not itv:
        raise HTTPException(status_code=404, detail="Interview not found")
    return itv


@router.get("/{interview_id}/questions", response_model=List[schemas.QuestionOut])
def list_interview_questions(interview_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    itv = db.query(models.Interview).filter(models.Interview.id == interview_id, models.Interview.user_id == current_user.id).first()
    if not itv:
        raise HTTPException(status_code=404, detail="Interview not found")
    return crud.list_questions(db, interview_id=interview_id)


# 다른 라우터 함수들도 함수 직접 호출로 수정
@router.post("/answer", response_model=schemas.FollowupOut)
def submit_answer(req: schemas.AnswerCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Validate ownership
    q = db.query(models.Question).filter(models.Question.id == req.question_id, models.Question.interview_id == req.interview_id).first()
    itv = db.query(models.Interview).filter(models.Interview.id == req.interview_id, models.Interview.user_id == current_user.id).first()
    if not q or not itv:
        raise HTTPException(status_code=404, detail="Question/Interview not found")

    # Save answer
    crud.create_answer(db, question_id=q.id, user_id=current_user.id, text=req.answer_text)

    # Generate exactly one follow-up for this answer - 함수 직접 호출
    follow_text = interview_service.generate_followup(previous_question=q.text, answer_text=req.answer_text)
    follow_audio_url = audio_service.synthesize_to_file(follow_text, filename_hint=f"followup-q{q.index_num}-interview{itv.id}")
    follow = crud.create_question(db, interview_id=itv.id, index_num=q.index_num, text=follow_text, is_followup=True, audio_url=follow_audio_url)

    return {"question": follow}


@router.post("/{interview_id}/finish")
def finish_interview(interview_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    itv = db.query(models.Interview).filter(models.Interview.id == interview_id, models.Interview.user_id == current_user.id).first()
    if not itv:
        raise HTTPException(status_code=404, detail="Interview not found")
    crud.set_interview_status(db, interview_id, "finished")
    return {"message": "감사합니다. 이로써 모의 면접은 끝났습니다.", "status": "finished"}
