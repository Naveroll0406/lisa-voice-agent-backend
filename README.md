# Lisa: AI Voice Assistant (Backend) 🎙️🏥

A highly sophisticated, real-time Voice AI backend built for modern healthcare and appointment management. This system powers **Lisa**, an autonomous front-desk agent capable of understanding natural human speech, querying a live SQLite database, booking appointments, and generating structured call summaries on the fly.

## 🚀 Key Features

- **Ultra-Low Latency Voice Pipeline:** Built on [LiveKit Agents](https://docs.livekit.io/agents/), utilizing Deepgram for real-time STT and Cartesia for ultra-realistic TTS.
- **Dynamic Tool Calling:** The agent autonomously invokes internal tools to fetch available slots, identify users by phone number, and prevent double-booking.
- **SQLite Database Integration:** Seamlessly integrated SQLAlchemy ORM for managing Users, Available Slots, and Appointments.
- **Background Summarization:** Automatically triggers an asynchronous LLM task at the end of every call to extract user preferences, summarize the interaction, and calculate real-time API cost breakdowns.
- **WebRTC Data Channels:** Streams tool execution states and final summary JSON payloads directly to the frontend via WebRTC data channels for instant UI updates.

## 🛠️ Tech Stack

- **Frameworks:** Python, FastAPI, LiveKit Agents
- **AI / LLMs:** OpenAI (`gpt-4o-mini`), Llama 3.3 70B (via OpenRouter)
- **Voice APIs:** Deepgram (STT), Cartesia (TTS)
- **Database:** SQLite (SQLAlchemy ORM)

## 📦 Installation & Setup

1. **Clone the repository and enter the directory:**
   ```bash
   cd lisa-voice-backend
   ```

2. **Set up a virtual environment and install dependencies:**
   ```bash
   conda create -n voice_ai python=3.11
   conda activate voice_ai
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add your API keys:
   ```env
   LIVEKIT_URL=wss://your-project.livekit.cloud
   LIVEKIT_API_KEY=your_key
   LIVEKIT_API_SECRET=your_secret
   DEEPGRAM_API_KEY=your_deepgram_key
   CARTESIA_API_KEY=your_cartesia_key
   OPENROUTER_API_KEY=your_openrouter_key
   ```

4. **Seed the Database (Optional but Recommended):**
   This generates standard working hours/slots for the agent to book against.
   ```bash
   python db/seed_slots.py
   ```

## ⚙️ Running the Agent

Start the LiveKit worker agent locally in development mode:
```bash
python agent/main.py dev
```

The agent will connect to the LiveKit Cloud room and wait for incoming web connections from the Next.js frontend!

## 🧩 Tool Calling Architecture

Lisa is equipped with the following strict deterministic tools:
- `identify_user(phone_number)` -> Features a strict Authentication Lock to prevent LLM hallucination and ensure User Profile data is securely broadcasted before allowing other tools to execute.
- `fetch_slots(date_str)`
- `book_appointment(phone_number, name, date_str, time_str, intent)`
- `retrieve_appointments(phone_number)`
- `cancel_appointment(phone_number, appointment_id)`
- `modify_appointment(phone_number, appointment_id, new_date, new_time)`
- `end_conversation()` -> Triggers the async Summary pipeline.
- `restart_session()` -> Sends a WebRTC action to force the frontend to reload for testing.

## 🏆 Hackathon Project
This repository serves as the backend infrastructure for the AI Voice Agent hackathon challenge.
