import os
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Depends, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware  
from sqlalchemy.orm import Session

# Import with absolute path relative to the backend folder
from db.session import get_db
from db.models import Conversation, Appointment, User
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=ENV_PATH)

app = FastAPI(title="Lisa Voice AI Backend")

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Update with Vercel frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "message": "Lisa Voice AI Backend is running"}

@app.get("/api/history/{phone_number}")
def get_history(phone_number: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    appointments = db.query(Appointment).filter(Appointment.user_id == user.id).all()
    return {"appointments": appointments}

@app.get("/api/summary/{conversation_id}")
def get_summary(conversation_id: int, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    return {
        "summary": conv.summary,
        "preferences": conv.preferences,
        "started_at": conv.started_at,
        "ended_at": conv.ended_at
    }
