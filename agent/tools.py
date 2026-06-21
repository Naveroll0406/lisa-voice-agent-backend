import sys
import os
import json
import asyncio
import urllib.request
from datetime import datetime

from sqlalchemy.exc import IntegrityError
# pyrefly: ignore [missing-import]
from livekit.agents import function_tool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.session import SessionLocal
from db.models import User, Slot, Appointment


def get_db():
    return SessionLocal()


# ==========================================================
# Globals for LiveKit Context
# ==========================================================
CURRENT_ROOM = None
CURRENT_SESSION = None

async def publish_tool_call(status: str, tool: str, label: str):
    """Sends a data channel message to the Next.js frontend to display the tool call visually."""
    if CURRENT_ROOM and CURRENT_ROOM.local_participant:
        try:
            payload = json.dumps({"type": "tool_call", "tool": tool, "status": status, "label": label})
            await CURRENT_ROOM.local_participant.publish_data(payload.encode("utf-8"))
        except Exception as e:
            print(f"Error publishing tool call data: {e}")


# ==========================================================
# Internal DB functions
# ==========================================================

def _identify_user(phone_number: str):
    db = get_db()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if not user:
            user = User(phone_number=phone_number)
            db.add(user)
            db.commit()
            db.refresh(user)
            result = {
                "status": "new_user",
                "user_id": user.id,
                "phone_number": phone_number,
            }
        else:
            result = {
                "status": "existing_user",
                "user_id": user.id,
                "name": user.name,
                "phone_number": user.phone_number,
            }
        return json.dumps(result)
    finally:
        db.close()


def _fetch_slots(date_str: str = ""):
    db = get_db()
    try:
        query = db.query(Slot)
        if date_str:
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
                query = query.filter(Slot.slot_date == d)
            except ValueError:
                pass

        booked_apps = db.query(Appointment).filter(Appointment.status == "booked").all()
        booked_set = {(app.slot_date, app.slot_time) for app in booked_apps}

        available = []
        for slot in query.all():
            if (slot.slot_date, slot.slot_time) not in booked_set:
                available.append(f"{slot.slot_date} at {slot.slot_time}")

        if not available:
            return "No slots available."
        return "Available slots: " + ", ".join(available)
    finally:
        db.close()


def _book_appointment(phone_number: str, name: str, date_str: str, time_str: str, intent: str):
    db = get_db()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if not user:
            return "User not identified."

        if name and not user.name:
            user.name = name
            db.commit()

        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        try:
            t = datetime.strptime(time_str, "%H:%M:%S").time()
        except ValueError:
            t = datetime.strptime(time_str, "%H:%M").time()

        appointment = Appointment(
            user_id=user.id,
            slot_date=d,
            slot_time=t,
            intent=intent,
            status="booked",
        )

        db.add(appointment)
        db.commit()
        return f"Successfully booked appointment for {date_str} at {time_str}."
    except IntegrityError:
        db.rollback()
        return "That slot is already booked. Double booking prevented!"
    except Exception as e:
        db.rollback()
        return str(e)
    finally:
        db.close()


def _retrieve_appointments(phone_number: str):
    db = get_db()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if not user:
            return "User not found."

        apps = db.query(Appointment).filter(Appointment.user_id == user.id, Appointment.status == "booked").all()
        if not apps:
            return "No active appointments found."

        return " | ".join([f"ID={a.id} (CRITICAL: DO NOT READ THIS ID ALOUD TO USER): {a.slot_date} at {a.slot_time}" for a in apps])
    finally:
        db.close()


def _cancel_appointment(phone_number: str, appointment_id: int):
    db = get_db()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if not user:
            return "User not found."

        app = db.query(Appointment).filter(Appointment.id == appointment_id, Appointment.user_id == user.id).first()
        if not app:
            return "Appointment not found."

        app.status = "cancelled"
        db.commit()
        return f"Appointment {appointment_id} cancelled."
    finally:
        db.close()


def _modify_appointment(phone_number: str, appointment_id: int, new_date: str, new_time: str):
    db = get_db()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if not user:
            return "User not found."

        app = db.query(Appointment).filter(Appointment.id == appointment_id, Appointment.user_id == user.id).first()
        if not app:
            return "Appointment not found."

        app.slot_date = datetime.strptime(new_date, "%Y-%m-%d").date()
        try:
            app.slot_time = datetime.strptime(new_time, "%H:%M:%S").time()
        except ValueError:
            app.slot_time = datetime.strptime(new_time, "%H:%M").time()

        db.commit()
        return f"Appointment {appointment_id} moved to {new_date} at {new_time}"
    except IntegrityError:
        db.rollback()
        return "That slot is already taken."
    finally:
        db.close()


# ==========================================================
# Background LLM Summarization
# ==========================================================

def _generate_summary_sync(transcript: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    prompt = (
        "You are an assistant creating a structured call summary. Based on the following transcript, "
        "extract the following information:\n"
        "- A brief 2-3 sentence summary of the conversation.\n"
        "- A list of appointments booked, modified, or cancelled (if any).\n"
        "- Any user preferences mentioned.\n"
        "Return the output as plain, clean text formatting."
    )
    
    data = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"TRANSCRIPT:\n{transcript}"}
        ]
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            return result['choices'][0]['message']['content']
    except Exception as e:
        return f"Summary generation failed: {str(e)}"

# ==========================================================
# LiveKit Tools
# ==========================================================

@function_tool
async def identify_user(phone_number: str):
    await publish_tool_call("running", "identify_user", f"Identifying user: {phone_number}...")
    res = _identify_user(phone_number)
    await publish_tool_call("done", "identify_user", "User identified ✅")
    return res


@function_tool
async def fetch_slots(date_str: str = ""):
    await publish_tool_call("running", "fetch_slots", "Fetching available slots...")
    res = _fetch_slots(date_str)
    await publish_tool_call("done", "fetch_slots", "Slots retrieved ✅")
    return res


@function_tool
async def book_appointment(
    phone_number: str,
    name: str,
    date_str: str,
    time_str: str,
    intent: str,
):
    await publish_tool_call("running", "book_appointment", "Booking your appointment...")
    res = _book_appointment(phone_number, name, date_str, time_str, intent)
    await publish_tool_call("done", "book_appointment", "Booking confirmed ✅")
    return res


@function_tool
async def retrieve_appointments(phone_number: str):
    await publish_tool_call("running", "retrieve_appointments", "Retrieving past appointments...")
    res = _retrieve_appointments(phone_number)
    await publish_tool_call("done", "retrieve_appointments", "Past bookings loaded ✅")
    return res


@function_tool
async def cancel_appointment(phone_number: str, appointment_id: int):
    await publish_tool_call("running", "cancel_appointment", f"Cancelling appointment {appointment_id}...")
    res = _cancel_appointment(phone_number, appointment_id)
    await publish_tool_call("done", "cancel_appointment", "Appointment cancelled ❌")
    return res


@function_tool
async def modify_appointment(phone_number: str, appointment_id: int, new_date: str, new_time: str):
    await publish_tool_call("running", "modify_appointment", "Rescheduling appointment...")
    res = _modify_appointment(phone_number, appointment_id, new_date, new_time)
    await publish_tool_call("done", "modify_appointment", "Appointment rescheduled 🔄")
    return res


@function_tool
async def end_conversation():
    await publish_tool_call("running", "end_conversation", "Ending conversation & generating summary...")
    
    # 1. Extract Transcript
    transcript = "No transcript available."
    word_count = 0
    if CURRENT_SESSION and hasattr(CURRENT_SESSION, '_chat_ctx') and CURRENT_SESSION._chat_ctx:
        messages = []
        
        ctx_msgs = CURRENT_SESSION._chat_ctx.messages
        if callable(ctx_msgs):
            ctx_msgs = ctx_msgs()
            
        for msg in ctx_msgs:
            role = str(getattr(msg, 'role', '')).lower()
            if 'user' in role or 'assistant' in role:
                content = getattr(msg, 'content', '')
                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, str): text_parts.append(part)
                        elif hasattr(part, 'text'): text_parts.append(part.text)
                        else: text_parts.append(str(part))
                    content = " ".join(text_parts)
                elif not isinstance(content, str):
                    content = str(content)
                
                if content.strip():
                    role_str = "USER" if "user" in role else "ASSISTANT"
                    messages.append(f"{role_str}: {content.strip()}")
        transcript = "\n".join(messages)
        word_count = len(transcript.split())
        
    # 2. Generate Summary via LLM (in background thread so we don't block event loop)
    summary_text = await asyncio.to_thread(_generate_summary_sync, transcript)
    
    # 3. Calculate Cost Breakdown
    # Using dummy industry-standard estimates for this hackathon
    llm_cost = word_count * 0.0001
    tts_cost = word_count * 0.0003
    stt_cost = word_count * 0.0002
    total_cost = llm_cost + tts_cost + stt_cost
    
    cost_breakdown = (
        f"Cost Breakdown:\n"
        f"- LLM Tokens: ${llm_cost:.4f}\n"
        f"- Cartesia TTS: ${tts_cost:.4f}\n"
        f"- Deepgram STT: ${stt_cost:.4f}\n"
        f"Total Call Cost: ${total_cost:.4f}"
    )
    
    # 4. Publish Summary to UI
    if CURRENT_ROOM and CURRENT_ROOM.local_participant:
        try:
            payload = json.dumps({
                "type": "summary", 
                "data": summary_text, 
                "cost": cost_breakdown,
                "timestamp": datetime.now().isoformat()
            })
            await CURRENT_ROOM.local_participant.publish_data(payload.encode("utf-8"))
        except Exception as e:
            print(f"Error publishing summary data: {e}")
        
    await publish_tool_call("done", "end_conversation", "Summary published ✅")
    return "Conversation completed. The summary has been sent to the user interface."