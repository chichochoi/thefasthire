#C:\Users\user\모든 개발\thefasthire\backend\app\services\interview_service.py
from typing import List, Tuple
from openai import OpenAI
import os
import base64

from .gcs_service import GCSService
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
SYSTEM_PROMPT = """당신은 전문적인 면접관입니다. 
주어진 이력서와 회사 정보를 바탕으로 적절한 면접 질문을 생성해주세요.
질문은 지원자의 경험과 역량을 평가할 수 있도록 구체적이고 실질적이어야 합니다."""
def build_initial_prompt(resume_text: str, company: str, role: str) -> str:
    return f"""
다음 이력서를 바탕으로 {company}의 {role} 직무에 적합한 면접 질문 5개를 생성해주세요.
각 질문에는 1, 2, 3, 4, 5 번호를 붙여주세요.

이력서 내용:
{resume_text}

회사: {company}
직무: {role}
"""
def build_followup_prompt(previous_question: str, answer_text: str) -> str:
    return f"""
다음은 이전 면접 질문과 지원자의 답변입니다.
이 답변을 바탕으로 적절한 꼬리질문 1개를 생성해주세요.

이전 질문: {previous_question}
지원자 답변: {answer_text}

꼬리질문:
"""
def build_initial_prompt_for_pdf(company: str, role: str) -> str:
    """PDF용 초기 프롬프트"""
    return f"당신은 {company}의 면접 사정관입니다. 첨부된 자소서와 {role} 직무에 맞는 면접 질문을 자소서와 회사 상황을 고려하여 1,2,3,4,5 인덱스를 붙여서 총 5개를 만드시오"
# 기존 텍스트 기반 함수 유지
def generate_questions(resume_text: str, company: str, role: str) -> List[Tuple[int, str]]:
    """
    DEPRECATED: PDF만 사용하므로 더 이상 필요없음
    """
    raise NotImplementedError("텍스트 이력서는 더 이상 지원하지 않습니다. PDF를 사용해주세요.")
# 새로운 PDF 기반 함수 추가
def generate_questions_from_pdf(file_path: str, company: str, role: str) -> List[Tuple[int, str]]:
    """
    PDF 파일 기반 질문 생성
    Returns [(index, question_text)*5]
    """
    try:
        gcs_service = GCSService()
        file_content = gcs_service.get_file_content(file_path)
        
        # Base64 인코딩
        base64_pdf = base64.b64encode(file_content).decode('utf-8')
        
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5-mini"),  # PDF 지원 모델
            messages=[
                {
                    "role": "system", 
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": build_initial_prompt_for_pdf(company, role)
                        },
                        {
                            "type": "text", 
                            "text": f"data:application/pdf;base64,{base64_pdf}"
                        }
                    ]
                }
            ],
            temperature=1,
        )
        
        text = resp.choices[0].message.content.strip()
        return _parse_questions(text)
        
    except Exception as e:
        raise Exception(f"PDF 기반 질문 생성 실패: {str(e)}")
def _parse_questions(text: str) -> List[Tuple[int, str]]:
    """질문 파싱 로직을 별도 함수로 분리"""
    items: List[Tuple[int, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Try formats like "1. ..." or "1) ..." or "1 ..."
        if line[0].isdigit():
            # Extract leading index
            parts = line.split(maxsplit=1)
            if len(parts) >= 2:
                idx_part = parts[0].replace(".", "").replace(")", "")
                if idx_part.isdigit():
                    idx = int(idx_part)
                    q = parts[1].strip()
                    items.append((idx, q))
    
    # Fallback: if parsing failed, split into 5 by sentences
    if len(items) < 5:
        parts = [p.strip("-• ").strip() for p in text.split("\n") if p.strip()]
        items = [(i+1, part) for i, part in enumerate(parts[:5])]
    
    return items[:5]
def generate_followup(previous_question: str, answer_text: str) -> str:
    """꼬리질문 생성 (기존 로직 유지)"""
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_followup_prompt(previous_question, answer_text)},
        ],
        temperature=1,
    )
    return resp.choices[0].message.content.strip()

