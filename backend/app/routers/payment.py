#C:\Users\user\모든 개발\thefasthire\backend\app\routers\payment.py
from fastapi import APIRouter, HTTPException, Depends, Form
from sqlalchemy.orm import Session
from ..database import get_db
import os


router = APIRouter(prefix="/payments", tags=["payments"])


# Placeholder: integrate Stripe/Bootpay/Cloud Payments as needed.
# This route can verify payment session and mark entitlement in DB.


@router.post("/verify")
def verify_payment(session_id: str = Form(...), db: Session = Depends(get_db)):
    # TODO: implement real gateway verification
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    # Assume verification succeeded
    return {"status": "verified", "session_id": session_id}
