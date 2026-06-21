# import os
# import asyncio
# from livekit.agents import AutoSubscribe, JobContext, JobRequest, WorkerOptions, cli
# from livekit.agents.pipeline import VoicePipelineAgent
# from livekit.plugins import deepgram, cartesia, openai
# from dotenv import load_dotenv

# import sys
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from agent.prompts import SYSTEM_PROMPT
# from agent.tools import (
#     identify_user, fetch_slots, book_appointment, retrieve_appointments, 
#     cancel_appointment, modify_appointment, end_conversation
# )
# from livekit.agents.llm import FunctionContext, ai_callable

# ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
# load_dotenv(dotenv_path=ENV_PATH)

# import json

# # We map the tools into LiveKit's FunctionContext
# # While the plan suggested LangGraph, LiveKit's VoicePipelineAgent requires its own fnc_ctx
# # for streaming low-latency voice. We use the same underlying DB functions.
# class MykareTools(FunctionContext):
#     def __init__(self, ctx: JobContext):
#         super().__init__()
#         self.ctx = ctx
        
#     async def _publish(self, status: str, tool: str, label: str):
#         if self.ctx and self.ctx.room and self.ctx.room.local_participant:
#             payload = json.dumps({"type": "tool_call", "tool": tool, "status": status, "label": label})
#             await self.ctx.room.local_participant.publish_data(payload)

#     @ai_callable(description="Identify the caller by phone number. Always call this first if the user isn't yet identified.")
#     async def identify_user(self, phone_number: str):
#         await self._publish("running", "identify_user", "Identifying user...")
#         res = identify_user(phone_number)
#         await self._publish("done", "identify_user", "User identified.")
#         return res

#     @ai_callable(description="Return available appointment slots, optionally filtered by date.")
#     async def fetch_slots(self, date: str = None):
#         await self._publish("running", "fetch_slots", "Fetching available slots...")
#         res = fetch_slots(date)
#         await self._publish("done", "fetch_slots", "Slots retrieved.")
#         return res

#     @ai_callable(description="Book an appointment for the identified user.")
#     async def book_appointment(self, phone_number: str, name: str, date: str, time: str, intent: str = ""):
#         await self._publish("running", "book_appointment", "Booking your appointment...")
#         res = book_appointment(phone_number, name, date, time, intent)
#         await self._publish("done", "book_appointment", "Booking confirmed.")
#         return res

#     @ai_callable(description="Get a user's past and upcoming bookings.")
#     async def retrieve_appointments(self, phone_number: str):
#         await self._publish("running", "retrieve_appointments", "Retrieving appointments...")
#         res = retrieve_appointments(phone_number)
#         await self._publish("done", "retrieve_appointments", "Appointments retrieved.")
#         return res

#     @ai_callable(description="Cancel an existing appointment.")
#     async def cancel_appointment(self, phone_number: str, appointment_id: int):
#         await self._publish("running", "cancel_appointment", "Cancelling appointment...")
#         res = cancel_appointment(phone_number, appointment_id)
#         await self._publish("done", "cancel_appointment", "Appointment cancelled.")
#         return res

#     @ai_callable(description="Reschedule an existing appointment to a new date/time.")
#     async def modify_appointment(self, phone_number: str, appointment_id: int, new_date: str, new_time: str):
#         await self._publish("running", "modify_appointment", "Rescheduling appointment...")
#         res = modify_appointment(phone_number, appointment_id, new_date, new_time)
#         await self._publish("done", "modify_appointment", "Appointment rescheduled.")
#         return res

#     @ai_callable(description="Call when the user is done — triggers summary generation and call wrap-up.")
#     async def end_conversation(self):
#         await self._publish("running", "end_conversation", "Ending conversation and generating summary...")
#         res = end_conversation()
#         await self._publish("done", "end_conversation", "Call ended.")
#         return res


# async def entrypoint(ctx: JobContext):
#     await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
#     fnc_ctx = MykareTools(ctx)
    
#     agent = VoicePipelineAgent(
#         vad=None, # LiveKit provides default VAD
#         stt=deepgram.STT(model="nova-3", api_key=os.getenv("DEEPGRAM_API_KEY")),
#         llm=openai.LLM(
#             base_url="https://openrouter.ai/api/v1",
#             api_key=os.getenv("OPENROUTER_API_KEY"),
#             model="meta-llama/llama-3.3-70b-instruct:free",
#         ),
#         tts=cartesia.TTS(
#             voice="248be419-c632-4f23-adf1-5324ed7dbf1d", # British lady voice as a default
#             api_key=os.getenv("CARTESIA_API_KEY")
#         ),
#         fnc_ctx=fnc_ctx,
#         chat_ctx=None, # Will initialize with system prompt
#     )
    
#     chat_ctx = agent.chat_ctx
#     chat_ctx.append(role="system", text=SYSTEM_PROMPT)

#     agent.start(ctx.room)

#     await asyncio.sleep(1)
#     await agent.say("Hi, I'm the Mykare virtual assistant. How can I help you with your appointments today?", allow_interruptions=True)

# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)

# pyrefly: ignore [missing-import]
from livekit.plugins import deepgram, cartesia, openai

from agent.prompts import SYSTEM_PROMPT
import agent.tools
from agent.tools import (
    identify_user,
    fetch_slots,
    book_appointment,
    retrieve_appointments,
    cancel_appointment,
    modify_appointment,
    end_conversation,
)

load_dotenv()


class LisaAssistant(Agent):
    def __init__(self):
        super().__init__(
            instructions=SYSTEM_PROMPT,
            tools=[
                identify_user,
                fetch_slots,
                book_appointment,
                retrieve_appointments,
                cancel_appointment,
                modify_appointment,
                end_conversation,
            ],
        )


async def entrypoint(ctx: JobContext):

    await ctx.connect()

    session = AgentSession(
        # Speech-to-Text
        stt=deepgram.STT(
            model="nova-3",
            api_key=os.getenv("DEEPGRAM_API_KEY"),
        ),

        # LLM
        llm=openai.LLM(
            # model="meta-llama/llama-3.3-70b-instruct:free",
            model = "openai/gpt-4o-mini",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        ),

        # Text-to-Speech
        tts=cartesia.TTS(
            voice="248be419-c632-4f23-adf1-5324ed7dbf1d",
            api_key=os.getenv("CARTESIA_API_KEY"),
        ),
    )

    agent.tools.CURRENT_ROOM = ctx.room
    agent.tools.CURRENT_SESSION = session

    await session.start(
        room=ctx.room,
        agent=LisaAssistant(),
    )

    await session.generate_reply(
        instructions="""
        Greet the user warmly.
        Introduce yourself as Lisa.
        IMMEDIATELY ask the user for their phone number so you can pull up their records.
        Keep the greeting brief and direct.
        """
    )


if __name__ == "__main__":

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )