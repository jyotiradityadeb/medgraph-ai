# MedGraph AI

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688)
![React](https://img.shields.io/badge/React-18-61DAFB)
![Neo4j](https://img.shields.io/badge/Neo4j-5.15-018BFF)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

MedGraph AI is a production-style multi-modal Graph RAG clinical knowledge navigator that combines vector retrieval (Qdrant), graph traversal (Neo4j), and LLM answer synthesis behind a FastAPI backend and React frontend designed for medical knowledge exploration and ingestion workflows.

## Architecture

```text
                        +------------------------------+
                        |         Frontend UI          |
                        |   React + Vite + Tailwind    |
                        +---------------+--------------+
                                        |
                                        v
                        +------------------------------+
                        |         FastAPI API          |
                        | Query | Ingest | Graph APIs  |
                        +---------------+--------------+
                                        |
                   +--------------------+--------------------+
                   |                                         |
                   v                                         v
        +--------------------------+              +--------------------------+
        |          Qdrant          |              |          Neo4j           |
        |  Vector Similarity Store |              |  Clinical Knowledge Graph|
        +--------------------------+              +--------------------------+
                   \                                         /
                    \               +---------------+       /
                     +-------------> |  LLM Layer    | <----+
                                     | OpenAI/Anthropic |
                                     +---------------+
```

## Prerequisites

- Docker Desktop 24+
- Docker Compose v2
- (Optional) GNU Make
- OpenAI and/or Anthropic API key for live LLM responses

## Quick Start

```bash
cp .env.example .env
docker-compose build
docker-compose up -d
docker-compose logs -f backend
open http://localhost:3000
```

## Fast Smoke Test

```bash
docker compose down
docker compose build backend frontend
docker compose up -d
docker compose ps
docker logs medgraph-backend
curl http://localhost:8000/health
curl http://localhost:6333
```

## Running the demo

### Step 1 — Start services
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
docker-compose up -d --build
```

### Step 2 — Wait for services to be healthy (60-90 seconds)
```bash
docker-compose ps
# All services should show "healthy" or "running"
```

### Step 3 — Seed the knowledge graph and vector data
```bash
docker-compose exec backend python scripts/seed_graph.py
docker-compose exec backend python scripts/seed_vectors.py
docker-compose exec backend python scripts/seed_demo_scenarios.py
```

### Step 4 — Verify everything works
```bash
docker-compose exec backend python scripts/demo_check.py
# Should print: STATUS: DEMO READY
```

### Step 5 — Open the app
http://localhost:3000

### Demo queries to try
- "Warfarin interactions in a patient on metformin and lisinopril"
- "Interpret: HbA1c 8.9%, BNP 450, eGFR 52"
- "Differential diagnosis for dyspnea with orthopnea and bilateral edema"
- "First-line treatment for T2DM with HbA1c 8.5%"
- "How does furosemide cause hypokalemia?"

### Troubleshooting
- If Neo4j takes too long: check docker-compose logs neo4j
- If models are slow first run: they are downloading, wait 2-3 min
- If OpenAI errors: check your API key in .env, fallbacks are active

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service health and dependency status |
| POST | `/api/v1/query` | Execute multi-modal Graph RAG query |
| POST | `/api/v1/query/intent` | Infer query intent and graph need |
| POST | `/api/v1/ingest` | Ingest clinical content into vector + graph stores |
| GET | `/api/v1/graph/context` | Retrieve graph neighborhood around entities |
| GET | `/api/v1/graph/stats` | Graph-level node/relationship counts |

## Demo Queries

- `What are first-line management options for type 2 diabetes with CKD?`
- `Show relationships between ACE inhibitors, hyperkalemia, and kidney function.`
- `What imaging findings suggest pulmonary embolism and which labs matter most?`
- `Compare anticoagulation options in atrial fibrillation with renal impairment.`

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Query, Zustand |
| Backend | FastAPI, Pydantic v2, SlowAPI, Structlog |
| Retrieval | Qdrant (vector DB), Neo4j (graph DB) |
| AI | OpenAI, Anthropic, Sentence Transformers |
| DevOps | Docker, Docker Compose, Nginx |

## Project Structure

```text
medgraph-ai/
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── README.md
├── Makefile
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── query.py
│   │   │   │   ├── ingest.py
│   │   │   │   └── graph.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── embeddings.py
│   │   │   ├── graph_rag.py
│   │   │   ├── multimodal.py
│   │   │   └── llm.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── qdrant_client.py
│   │   │   └── neo4j_client.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── logging.py
│   └── scripts/
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    ├── tailwind.config.js
    ├── public/
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api/
        │   └── client.ts
        ├── components/
        │   ├── QueryPanel/
        │   ├── GraphVisualization/
        │   ├── ResultsPanel/
        │   ├── ModalityUploader/
        │   └── Layout/
        ├── hooks/
        ├── store/
        ├── types/
        └── utils/
```
