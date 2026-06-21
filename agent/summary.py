import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.session import SessionLocal
from db.models import Conversation

llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", "dummy"),
    model="meta-llama/llama-3.3-70b-instruct:free",
)

def generate_summary(conversation_id: int, transcript: str):
    sys_msg = SystemMessage(content="You are an assistant that summarizes medical booking conversations in 3 bullet points. List appointments touched, list preferences, add a timestamp.")
    human_msg = HumanMessage(content=f"Transcript: {transcript}")
    
    response = llm.invoke([sys_msg, human_msg])
    summary_text = response.content
    
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            conv.summary = summary_text
            db.commit()
    finally:
        db.close()
        
    return summary_text
