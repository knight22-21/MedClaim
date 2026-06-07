# MedClaim — Autonomous Insurance Claim Lifecycle Agent

[![CI](https://github.com/YOUR_USERNAME/MedClaim/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/MedClaim/actions/workflows/ci.yml)

> **Multi-agent AI system that autonomously processes medical insurance claims — from clinical documentation through coding audit, denial prediction, and appeal generation — in under 90 seconds.**

MedClaim compresses what currently takes a billing specialist 2–4 hours per claim into autonomous agentic processing, targeting the **$262–300 billion** annual loss from denied insurance claims in the US alone.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Interface Layer                              │
│   React Vite Dashboard  │  Voice AI (Whisper + Coqui)  │  REST API │
├─────────────────────────────────────────────────────────────────────┤
│                   FastAPI Backend (Render)                          │
├─────────────────────────────────────────────────────────────────────┤
│              LangGraph Multi-Agent Orchestration                    │
│  ┌───────────┐  ┌──────────┐  ┌────────────┐  ┌────────────────┐  │
│  │ Eligibility│  │Code Audit│  │  Denial    │  │ Appeal Drafting│  │
│  │   Agent   │  │  Agent   │  │ Prediction │  │    Agent       │  │
│  └───────────┘  └──────────┘  └────────────┘  └────────────────┘  │
│                    Supervisor (Deterministic Router)                 │
├─────────────────────────────────────────────────────────────────────┤
│                   RAG Knowledge Layer (Qdrant)                      │
│   coding_rules │ payer_policies │ denial_patterns │ clinical_guides │
├─────────────────────────────────────────────────────────────────────┤
│              Persistence & Observability                            │
│   Supabase PostgreSQL │ Upstash Redis │ LangSmith │ Prometheus     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🎯 Target Markets

| Market | Payers | Coding Standard | Regulatory Body |
|--------|--------|----------------|-----------------|
| **US** (Primary) | Medicare, Medicaid, BCBS, Aetna, UHC, Cigna | ICD-10-CM + CPT/HCPCS | CMS |
| **India** (Secondary) | Star Health, HDFC Ergo, ICICI Lombard, PM-JAY | ICD-10 + HBP codes | IRDAI / NHA |

## 📁 Project Structure

```
MedClaim/
├── backend/
│   ├── app/              # FastAPI application (routes, models, services)
│   ├── agents/           # LangGraph agent modules (6 agents)
│   ├── rag/              # RAG pipeline (Qdrant setup, embeddings, retrievers)
│   ├── llmops/           # Observability (LangSmith, Prometheus, structlog)
│   ├── prompts/          # Versioned Jinja2 prompt templates
│   └── tests/            # Pytest test suite
├── frontend/             # React Vite billing dashboard
├── data/                 # Fixtures and ingestion scripts
├── infra/                # Docker Compose, Prometheus, Grafana configs
└── .github/workflows/    # CI/CD pipeline
```

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **LLM** | Groq (Llama 3.1 70B) + Gemini 1.5 Flash | Agent reasoning + long-context |
| **Orchestration** | LangGraph | Multi-agent state machine |
| **RAG** | Qdrant Cloud + Ollama (nomic-embed-text) | 4-collection knowledge base |
| **Backend** | FastAPI | REST API + async background tasks |
| **Database** | Supabase PostgreSQL | Claim state persistence |
| **Cache/Queue** | Upstash Redis (Optional) | Rate limiting |
| **Frontend** | React (Vite) + Tailwind CSS | Billing staff dashboard |
| **Voice** | Whisper + Coqui XTTS-v2 | Speech interface |
| **Observability** | LangSmith + Prometheus + Grafana | Full LLMOps stack |
| **Documents** | WeasyPrint + Jinja2 | PDF appeal letter generation |
| **EHR** | HAPI FHIR (Docker) | HL7 FHIR R4 simulation |

> **All infrastructure runs on free tiers. Zero dollars spent.**

## 🚀 Local Setup

### Prerequisites

- Python 3.11+
- Docker Desktop
- [Ollama](https://ollama.com) installed locally
- API keys for: Groq, Google AI Studio, Qdrant Cloud, Supabase, LangSmith, Upstash

### Quick Start

```bash
# 1. Clone and enter the repository
git clone https://github.com/YOUR_USERNAME/MedClaim.git
cd MedClaim

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Start infrastructure services
docker compose -f infra/docker-compose.yml up -d

# 6. Pull the embedding model
ollama pull nomic-embed-text

# 7. Run the FastAPI development server
uvicorn backend.app.main:app --reload --port 8000

# 8. Run tests
pytest backend/tests/ -v
```

### Service URLs (Local)

| Service | URL |
|---------|-----|
| FastAPI Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| HAPI FHIR | http://localhost:8080/fhir/metadata |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin/medclaim) |

## 🎥 Demo Scenario

To showcase the full capability of MedClaim:
1. Run the `generate_claims.py` script to seed Qdrant with history.
2. Submit a synthetic claim with known coding errors via the Dashboard.
3. Watch the claim transition through `QUEUED` -> `RUNNING` -> `HUMAN_REVIEW_REQUIRED`.
4. Review the auto-generated Code Audit report and its confidence scores.
5. Approve corrections and watch the Denial Risk Score drop.
6. Trigger the Voice AI from the dashboard to ask: "What is the status of my claim?"

## 📜 License

[MIT](LICENSE)
