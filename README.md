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
