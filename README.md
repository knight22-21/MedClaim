# 🏥 MedClaim — Autonomous Insurance Claim Lifecycle System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange)](https://python.langchain.com/docs/langgraph)
[![Groq](https://img.shields.io/badge/LLM-Groq_Llama_3.1-black)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **An enterprise-grade, multi-agent AI system that autonomously processes medical insurance claims — from clinical documentation through coding audit, denial prediction, and appeal generation — in under 90 seconds.**

---

## 📖 Executive Summary
Medical insurance claim denials represent a **$262B–$300B annual loss** in the US healthcare system. A human billing specialist takes 2 to 4 hours to manually audit a claim, cross-reference payer policies, and draft an appeal letter. 

**MedClaim** replaces this tedious manual workflow with a **deterministic, LangGraph-orchestrated multi-agent state machine**. Utilizing Retrieval-Augmented Generation (RAG) across four distinct medical vector databases, intelligent LLM routing (Groq for speed, Gemini 1.5 Flash for massive context windows), and a full production LLMOps observability suite, MedClaim drastically reduces resolution time while maintaining compliance through strict Human-in-the-Loop (HITL) gateways.

---

## 🏗️ System Architecture

MedClaim is composed of six modular, decoupling layers working in tandem:

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        INTERFACE LAYER                              │
│   React (Vite) Dashboard │  Voice AI (Whisper + Coqui) │  REST API  │
├─────────────────────────────────────────────────────────────────────┤
│                    APPLICATION BACKEND                              │
│            FastAPI (Async) + Redis Token Rate Limiter               │
├─────────────────────────────────────────────────────────────────────┤
│              MULTI-AGENT ORCHESTRATION (LANGGRAPH)                  │
│                                                                     │
│  ┌───────────┐  ┌──────────┐  ┌────────────┐  ┌────────────────┐    │
│  │ Eligibility│─▶ Code Audit│─▶   Denial   │─▶ Appeal Drafting │    │
│  │   Agent   │  │  Agent   │  │ Prediction │  │    Agent       │    │
│  └───────────┘  └──────────┘  └────────────┘  └────────────────┘    │
│            Supervisor Node (Deterministic Edge Router)              │
├─────────────────────────────────────────────────────────────────────┤
│                   RAG KNOWLEDGE LAYER (QDRANT)                      │
│   coding_rules │ payer_policies │ denial_patterns │ clinical_guides │
├─────────────────────────────────────────────────────────────────────┤
│              PERSISTENCE & CONTINUOUS LEARNING                      │
│  Supabase PostgreSQL (State) │ Supabase Edge Functions (Feedback)   │
├─────────────────────────────────────────────────────────────────────┤
│                  LLMOPS & OBSERVABILITY                             │
│   LangSmith (Tracing/Evals) │ Prometheus (Metrics) │ Grafana (UI)   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 How the Agents Work

At the core of MedClaim is a **LangGraph State Machine**. Unlike naive LLM chains, MedClaim uses a **Deterministic Supervisor Node** to route claims between specialized agents based on strict conditional Python logic. The agents share a `ClaimState` object that gets updated at every node.

1. **Eligibility Agent:** Acts as the first gatekeeper. It hits a mock hospital API to verify if the patient's insurance was active on the date of service and if the provider is in-network. If it fails, the pipeline halts immediately to save compute.
2. **Code Audit Agent:** Performs dense RAG. It queries the `coding_rules` Qdrant vector index for official ICD-10-CM and CPT guidelines. It hands these rules to the Groq LLM to check for Upcoding, Unbundling, or Missing Modifiers, returning a strictly typed JSON output using Pydantic parsers.
3. **Denial Prediction Agent:** Queries the `denial_patterns` Qdrant collection to find historical claims similar to the current one. It generates a probabilistic **Denial Risk Score (0-100)** and flags the exact reasons why a payer might reject the claim.
4. **Appeal Drafting Agent:** Triggered only if a claim is denied. It queries the `payer_policies` index for the specific legal clause the payer used, and the `clinical_guidelines` index for medical necessity proof. It routes to **Gemini 1.5 Flash** (to handle massive 1M+ token policy PDFs) to generate a legally sound, highly formal HTML/PDF appeal letter.
5. **Resolution Tracker (Background Task):** A continuous watcher that alerts managers via email if claims or appeals are approaching their regulatory filing deadlines.

---

## 🛠️ Technology Stack & Roles

Every technology in this stack was chosen to maximize speed, reliability, and cost-efficiency (the entire architecture can be run on free tiers).

### 🧠 AI & Orchestration
* **LangGraph:** Orchestrates the multi-agent state machine. Crucial for persisting states across steps and deterministic routing.
* **Groq (Llama 3.1 70B):** The primary LLM. Chosen for its extreme inference speed (500+ tokens/sec), making real-time sequential agent workflows viable.
* **Google Gemini 1.5 Flash:** The secondary LLM. Handles tasks requiring massive context windows, such as injecting 100-page payer policy PDFs into the Appeal Drafting Agent.
* **LangChain:** Utilized exclusively for prompt management, LLM wrappers, and Pydantic output parsing.

### 📚 RAG & Vector Databases
* **Qdrant:** The vector database powering the semantic search over medical rules. Segregated into 4 distinct collections to prevent cross-contamination of contexts.
* **LlamaIndex:** Handles ingestion, chunking (512 tokens + 64 token overlap), and metadata extraction for massive policy PDFs.
* **Ollama (nomic-embed-text):** Runs locally to generate 768-dimensional text embeddings at zero cost.

### 🌐 Backend & Persistence
* **FastAPI:** Provides an async HTTP layer capable of non-blocking LLM execution. 
* **Supabase (PostgreSQL):** Stores relational claim data, agent decisions, and audit outcomes. Utilizes **Supabase Realtime** to push live WebSocket updates to the frontend.
* **Upstash Redis:** Acts as an asynchronous rolling-window token tracker to implement a Circuit Breaker, protecting the system from Groq's 6,000 tokens/minute rate limit.
* **HAPI FHIR:** An HL7 FHIR R4 standard simulator that demonstrates integration capability with enterprise hospital Electronic Health Record (EHR) systems.

### 🖥️ Frontend & Interface
* **React (Vite) + TailwindCSS + ShadCN:** A beautifully responsive, glassmorphic dashboard for billing specialists to view claim states and approve agent interventions.
* **Whisper + Coqui XTTS-v2:** Powers the Voice AI interface, allowing billing staff to literally talk to the dashboard (e.g., *"What is the status of claim C-1042?"*).

### 🛡️ LLMOps & Observability
* **LangSmith:** Captures full trace trees of every LangGraph node, LLM call, and RAG retrieval. Also hosts our automated **Evaluation Suite** to catch prompt regressions.
* **Prometheus & Grafana:** Infrastructure-level observability. Tracks HTTP latencies, Groq token burn rates, and RAG retrieval similarity scores in real-time.
* **Structlog:** Emits structured, machine-readable JSON logs for deterministic tracking.

---

## 🔄 The Continuous Learning Loop
MedClaim doesn't just process claims; it learns. 

When a human billing specialist marks an appeal as `APPROVED_ON_APPEAL`, a Supabase trigger fires a webhook to the FastAPI backend (`POST /feedback/claim-outcome`). The backend extracts the entire context of that successful claim, converts it to an embedding via Ollama, and silently upserts it into the `denial_patterns` Qdrant vector index. The next time the Denial Prediction Agent evaluates a similar claim, it actively uses this newly learned strategy as a few-shot example.

---

## 📁 Project Structure

```text
MedClaim/
├── backend/
│   ├── app/              # FastAPI routers, Pydantic models, and Supabase services
│   ├── agents/           # LangGraph nodes (Supervisor, CodeAudit, Appeal, etc.)
│   ├── rag/              # Qdrant client, chunking logic, and ingestion scripts
│   ├── llmops/           # Prometheus metrics, LangSmith Evaluator, structured logging
│   └── tests/            # Pytest suite (Unit, Integration, and LLM output tests)
├── frontend/             # React (Vite) billing dashboard and UI components
├── data/                 # Medical fixtures and the Synthetic Claim Generator
└── infra/                # Docker Compose, Prometheus config, Grafana Dashboards
```

---

## 🚀 Setup & Installation

**Prerequisites:** Python 3.11+, Docker Desktop, Ollama (with `nomic-embed-text` pulled).

1. **Clone & Install Dependencies**
   ```bash
   git clone https://github.com/YOUR_USERNAME/MedClaim.git
   cd MedClaim
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   Copy the example environment file and fill in your free-tier API keys.
   ```bash
   cp .env.example .env
   ```

3. **Spin up the Observability Stack & FHIR Server**
   ```bash
   docker-compose -f infra/docker-compose.yml up -d
   ```

4. **Seed the Databases**
   Run the synthetic data generator to populate Qdrant with historical denial patterns.
   ```bash
   python -m data.generate_claims
   ```

5. **Start the Application**
   ```bash
   # Terminal 1: Backend
   uvicorn backend.app.main:app --reload --port 8000
   
   # Terminal 2: Frontend
   cd frontend
   npm install && npm run dev
   ```

---

## 🎥 Demo Walkthrough

To showcase the full capability of MedClaim:
1. Open the dashboard at `http://localhost:5173`.
2. View the **Grafana Dashboard** at `http://localhost:3001` to monitor active token consumption and agent latencies.
3. Submit a synthetic claim with known coding errors via the UI.
4. Watch the claim transition seamlessly through `QUEUED` ➔ `RUNNING` ➔ `HUMAN_REVIEW_REQUIRED` via WebSockets.
5. Review the auto-generated **Code Audit Report** and its RAG-backed confidence scores.
6. Approve the LLM's suggested corrections and watch the Denial Risk Score plummet in real-time.
7. Trigger the **Voice AI** from the dashboard to ask: *"What is the status of my claim?"*

---

### 📜 License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
