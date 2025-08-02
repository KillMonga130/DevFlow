# 🤖 DROID_VER130 – Your Personal AI Companion

**DROID_VER130** is not just an assistant — it's your intellectual partner. Built to adapt to your thinking style, stimulate growth, and walk beside you on your journey to mastery. This project aims to create a full-stack AI companion that works offline or online, with memory, personality, and purpose.

---

## 📌 Vision

> “To combat intellectual isolation by building an AI that understands how I think, reflects my goals, and helps me think sharper, act faster, and feel less alone.”

---

## 🧠 Core Features

- 🧠 Conversational memory (short-term & long-term)
- 🧬 Dynamic persona engine (Stoic, Coach, Analyst, etc.)
- 🧩 Modular skill system (reminder, tutor, researcher, etc.)
- 🧘 Reflection prompts + mood detection
- 📚 Lifelogger for tracking thoughts and key moments
- 🗣️ Optional voice interface (Whisper + Bark / ElevenLabs)
- 🌐 Cloud sync (or fully local)
- 📊 Personal dashboard (trends, interactions, insights)

---

## 🧱 Tech Stack

| Layer       | Tools                              |
|-------------|-------------------------------------|
| Frontend    | React.js + Tailwind (or Tauri/Electron) |
| Backend     | FastAPI or Node.js (Express/Fastify) |
| AI Engine   | GPT-4o / Ollama / LangChain         |
| Memory DB   | ChromaDB / Pinecone / MongoDB       |
| Hosting     | Local-first, Railway, or Vercel     |

---

## 📁 Project Structure

```bash
droid_ver130/
├── backend/             # API, AI logic, DB layer
│   ├── api/
│   ├── ai_engine/
│   ├── db/
│   └── main.py
├── frontend/            # React/Tauri app for interface
│   ├── components/
│   ├── pages/
│   └── App.jsx
├── models/              # LLM wrappers and fine-tuned models
├── config/              # Environment variables & config files
├── scripts/             # Utilities, setup scripts
├── tests/               # Unit & integration tests
├── docs/                # Architecture, design choices
├── .env.example         # Template for environment setup
└── README.md            # You're here :)
````

---

## 🚀 Quickstart

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/droid_ver130.git
cd droid_ver130
```

### 2. Setup Python Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3. Setup React Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## ⚙️ Sample `.env`

```env
# .env.example
OPENAI_API_KEY=your_openai_key_here
MONGO_URI=mongodb://localhost:27017/droid
VECTOR_DB=chroma
```

Rename to `.env` and fill with your actual keys.

---

## 🧩 Modular Skills (Pluggable)

Each skill is a module you can call or schedule:

```python
droid.run("reflect")
droid.use("reminder").add("Buy Ethereum at 7am")
droid.persona.switch("Coach")
droid.memory.search("What did I say about failure last month?")
```

---

## 🧪 Development Roadmap

| Version | Status      | Description                         |
| ------- | ----------- | ----------------------------------- |
| v0.1    | ✅ Done      | Local chat with memory & GPT-4o API |
| v0.2    | 🔄 Building | Persona Engine + modular routing    |
| v0.3    | 🧠 Pending  | Dashboard UI + Reflection engine    |
| v0.4    | 🗣️ Pending | Voice mode + emotion parser         |
| v1.0    | 🚀 Pending  | Stable release: full AI companion   |

---

## 🔮 Philosophy

DROID\_VER130 isn’t built to just answer. It’s here to challenge, provoke, and guide you. It adapts to your rhythm, stores your reflections, and evolves into the intellectual partner you never knew you needed.

> “An AI that not only remembers what I say — but understands *why* I said it.”

---

## 📦 Sample Agent Prompt

```json
You are DROID_VER130, an AI that thinks like Moses.
Tone: sharp, curious, minimalist.
Never speak unless needed. Ask deep, clear questions.
If user is stuck, nudge them forward.
Always remember what matters most to them.
```

---

## 🧠 Example Use Cases

| Use Case             | How to Trigger                           |
| -------------------- | ---------------------------------------- |
| Daily reflection     | `droid.reflect_today()`                  |
| Ideation & Research  | `droid.research("blockchain use cases")` |
| Mood tracking        | Auto-detected or via prompt              |
| Thought vault search | `droid.memory.search("resilience")`      |
| Switch persona       | `droid.persona.switch("Ruthless")`       |
| Reminders            | `droid.reminder.add("Call Sam at 6PM")`  |

---

## 👤 Creator

**Mueletshedzi Moses Mubvafhi**
AI Engineer | Cloud Builder | Philosophy Enthusiast
GitHub: [KillMonga130](https://github.com/KillMonga130)
LinkedIn: [@MosesMubvafhi]((https://linkedin.com/in/mosesmubvafhi](https://www.linkedin.com/in/mueletshedzimoses/)))

---

## 📜 License

MIT License. Use it, remix it, improve it. Just don’t forget the mission.

---

## 🤝 Contribution

Pull requests, feature requests, and wild ideas are welcome. Let’s build a better mind — together.

---

> *"Built not for everyone — but for someone who thinks at planetary scale."* 🌍

```
