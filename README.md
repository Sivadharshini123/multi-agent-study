# LearnWise — Syllabus-Grounded Multi-Agent RAG Study Companion

**LearnWise** is an AI-powered study assistant built specifically for 12th-standard students studying fixed state/matriculation syllabi. Unlike generic search engines or open-ended chatbots that return overwhelming or out-of-syllabus answers, LearnWise grounds every explanation, quiz, and study schedule strictly in the student's uploaded textbook PDF.

---

## Key Features

* **Single-Book Session Isolation:** Students upload one textbook PDF at a time, eliminating cross-subject retrieval noise and keeping vector search fast and focused.
* **Hybrid RAG Pipeline:** Combines dense semantic search (**`all-MiniLM-L6-v2` + ChromaDB**) with sparse keyword matching (**BM25**) via **Reciprocal Rank Fusion (RRF)** to accurately retrieve definitions, formulas, and derivations with exact textbook page citations.
* **Stateful Multi-Agent Orchestration (LangGraph):** Coordinates **5 specialized AI agents** over a shared `StateGraph` rather than relying on a single overloaded prompt:
  1. **Tutor (RAG) Agent:** Answers syllabus questions using only retrieved textbook chunks (`temperature=0.0`) with exact page citations.
  2. **Quiz Generator Agent:** Creates textbook-grounded Multiple-Choice Questions (MCQs) on demand.
  3. **Quiz Reviewing Agent:** Evaluates student submissions against textbook passages, providing targeted hints and explanations.
  4. **Progress Tracking Agent:** Condenses quiz results into structured `weak_topics` across study sessions.
  5. **Scheduling Agent:** Generates personalized daily revision timetables prioritizing weak concepts.
* **Human-in-the-Loop Pause & Resume:** Uses LangGraph `interrupt()` and **`PostgresSaver`** (`psycopg`) to suspend execution while a student solves a quiz in React and resume seamlessly upon submission without regenerating questions.
* **Hallucination & Prompt-Injection Guardrails:** Enforces pre-LLM cosine similarity thresholds (rejecting out-of-syllabus queries before calling the LLM), XML tag isolation, and strict Pydantic JSON output schemas.

---

## System Architecture

```text
┌───────────────────┐     REST API (JSON)      ┌──────────────────────────────────────────────┐
│   React Frontend  │ ───────────────────────► │            Python FastAPI Backend            │
│  (Student Portal) │ ◄─────────────────────── │                                              │
└───────────────────┘                          │  ┌────────────────────────────────────────┐  │
                                               │  │         LangGraph StateGraph           │  │
                                               │  │   Router ─► Tutor / Quiz / Reviewer    │  │
                                               │  │          ─► Tracker ─► Scheduler       │  │
                                               │  └───────────┬────────────────┬───────────┘  │
                                               │              │                │              │
                                               │              ▼                ▼              │
                                               │  ┌──────────────────┐  ┌──────────────────┐  │
                                               │  │  Hybrid RAG      │  │   PostgreSQL     │  │
                                               │  │  ChromaDB + BM25 │  │ (PostgresSaver / │  │
                                               │  │  (Local MiniLM)  │  │  psycopg3 State) │  │
                                               │  └──────────────────┘  └──────────────────┘  │
                                               └──────────────────────┬───────────────────────┘
                                                                      │ HTTPS (OpenRouter API)
                                                                      ▼
                                               ┌──────────────────────────────────────────────┐
                                               │     Claude 3 Haiku (LLM Inference Tier)      │
                                               └──────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React | Interactive study UI for textbook upload, Q&A chat, quizzes, and study schedules |
| **Backend API** | Python, FastAPI, Pydantic | Async REST endpoints, request validation, and structured JSON output enforcement |
| **Agent Orchestration** | LangGraph (`StateGraph`) | Stateful multi-agent routing, conditional edges, and `interrupt()` pause/resume |
| **LLM Inference** | Claude 3 Haiku (via OpenRouter API) | Sub-second, low-cost generation across all five specialized agent roles |
| **Vector Store & Embeddings** | ChromaDB, `all-MiniLM-L6-v2` | Local 384-dimensional dense vector indexing with zero cloud retrieval latency |
| **Hybrid Search & Parsing** | PyMuPDF (`fitz`), BM25, RRF | Page-tagged PDF chunking and hybrid semantic + exact-keyword ranking |
| **Relational & State DB** | PostgreSQL (`langgraph-checkpoint-postgres`, `psycopg`) | Persistent `thread_id` graph checkpoints, user metadata, and quiz history |

---

## How the Pipeline Works

1. **PDF Ingestion & Deduplication:**
   * When a student uploads a textbook PDF in React, FastAPI computes a SHA-256 file hash to skip re-indexing previously uploaded books.
   * `PyMuPDF` extracts text page-by-page with inline `[[PAGE_X]]` markers, splits it using `RecursiveCharacterTextSplitter` (1,000-character chunks, 200-character overlap), and stores `page_start` / `page_end` metadata in both **ChromaDB** and a serialized **BM25** index.
2. **Hybrid Retrieval & Guardrail Gate:**
   * Incoming questions run in parallel across **ChromaDB** (cosine similarity) and **BM25** (keyword matching)**.
   * If top retrieval scores fall below a strict similarity threshold, the backend immediately returns an out-of-syllabus notice without invoking the LLM.
3. **Multi-Agent Execution & Checkpointing:**
   * A **Router Node** directs the request along conditional edges to the **Tutor**, **Quiz**, or **Scheduler** flow.
   * Every node transition persists a snapshot in **PostgreSQL** via `PostgresSaver`, enabling multi-session progress tracking and seamless quiz pause/resume.

---

## Getting Started

### Prerequisites
* Python 3.10+
* Node.js 18+ & npm
* PostgreSQL 14+
* An **OpenRouter API Key** (for `anthropic/claude-3-haiku`)

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/learnwise.git](https://github.com/your-username/learnwise.git)
cd learnwise
```

### 2. Backend Setup (FastAPI + LangGraph)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file inside `backend/`:
```env
OPENROUTER_API_KEY=sk-or-v1-your-api-key-here
POSTGRES_URI=postgresql://postgres:password@localhost:5432/learnwise
CHROMA_PERSIST_DIR=./chroma_db
```

Run the FastAPI server:
```bash
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup (React)
```bash
cd ../frontend
npm install
npm run dev
```

---

## Security & Architecture Highlights

* **Zero Browser Key Exposure:** React communicates exclusively with FastAPI REST endpoints; `OPENROUTER_API_KEY` and `POSTGRES_URI` remain strictly in server-side `.env` variables.
* **Prompt Injection Isolation:** Student queries and retrieved textbook passages are wrapped in distinct XML delimiters (`<student_query>`, `<textbook_context>`) with role-locked system prompts.
* **Low End-to-End Latency:** Keeping `all-MiniLM-L6-v2` and `ChromaDB` local eliminates external vector DB round-trips, while pairing them with **Claude 3 Haiku** keeps multi-agent chains fast and cost-efficient.
