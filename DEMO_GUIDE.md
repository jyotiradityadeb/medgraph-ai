# MedGraph AI — Live Demo Guide

## Pre-demo setup (5 minutes before)

```bash
# 1. Start all services
docker-compose up -d

# 2. Verify system is ready
python backend/scripts/validate_system.py

# 3. Seed demo data (if not already done)
make seed

# 4. Open tabs:
# - Tab 1: http://localhost:3000 (MedGraph AI — FULL SCREEN)
# - Tab 2: http://localhost:7474 (Neo4j Browser — for graph viz)
# - Tab 3: http://localhost:8000/docs (API docs — for technical questions)
```

## Demo script (8 minutes)

### Opening statement (30 seconds)
"MedGraph AI is a clinical knowledge platform that answers complex medical questions by combining three AI components: multi-modal vector retrieval across clinical text, medical images, audio transcripts, and lab tables — a medical knowledge graph with drug-disease-symptom ontology — and an LLM that synthesizes both into grounded, cited answers. Let me show you what that looks like in practice."

### Demo 1: Drug interaction scenario (2 min)
Click "Warfarin interactions in elderly patients with AF" example query, or type:
"Patient is 72yo with T2DM, HTN, and AF on warfarin 5mg, metformin, and lisinopril. Just prescribed clarithromycin for pneumonia. What interactions should I know about?"

POINT OUT as response streams in:
- Metadata bar: "drug_interaction" intent, confidence score, modalities used
- ⚠️ WARNING boxes appearing for interactions
- [Doc N] citation superscripts
- Graph nodes count increasing

### Demo 2: Lab interpretation (1.5 min)
Click "Interpret: HbA1c 8.9%, BNP 450, eGFR 52" or type it.
POINT OUT: Table modality source card in sources panel. Graph showing DM + Heart Failure + CKD nodes connected.

### Demo 3: Graph Explorer (2 min)
Switch to Graph page. Search "Warfarin".
POINT OUT:
- Force-directed layout settling
- Blue drug nodes, red disease nodes, amber symptom nodes
- Hover to highlight edges
- Click Warfarin node → NodeDetailPanel showing all properties
- "TREATS", "INTERACTS_WITH", "CONTRAINDICATED_FOR" edges visible
- Click "Explore from this node" → graph re-centers

### Demo 4: Data Ingest (1 min)
Go to Ingest page. Paste a clinical note in Clinical Note section.
POINT OUT: Processing happens in real time. "Now this note is instantly searchable."

### Closing (30 seconds)
"The architecture combines Qdrant for multi-modal vector search, Neo4j for graph traversal up to 2-3 hops, and GPT-4o for synthesis. The key insight is that graph traversal finds relationships that semantic similarity misses — like tracing warfarin through CYP2C9 to dosing implications in CKD patients. That multi-hop reasoning is impossible with pure vector search."

## Likely evaluator questions and answers

**Q: How is this different from just using ChatGPT with medical documents?**
A: Three differences. First, the responses are grounded in your specific ingested data — [Doc 1] means that source was actually retrieved. Second, the knowledge graph adds structured medical facts that never hallucinate — drug interaction severity comes from the graph, not LLM memory. Third, multi-modal retrieval finds relevant lab tables and images that text search would miss.

**Q: How does the graph traversal actually work?**
A: The query is first parsed by GPT-4o to extract entity names — drugs, diseases, symptoms. Those entities are matched to Neo4j nodes. We then run a Cypher query with *1..2 relationship hops to find connected nodes. The resulting subgraph is converted to natural language and appended to the LLM prompt. So the LLM sees both retrieved text AND graph relationships simultaneously.

**Q: What is Reciprocal Rank Fusion?**
A: Each modality returns results with their own relevance scores — CLIP scores for images, cosine similarity for text. Those scales are incomparable, so you can't average them. RRF converts each result's rank into a score using 1/(rank + 60). A document ranked #1 in text search AND #2 in table search gets a higher RRF score than one ranked #1 in only one modality. It's rank-based, not score-based, so it works across incomparable scoring systems.

**Q: How do you prevent hallucination?**
A: Three layers. The system prompt instructs the model to only cite retrieved documents and to say "I don't have information" rather than speculate. The knowledge graph provides verified structured facts — drug-disease relationships are from the seeded ontology, not generated. And temperature is set to 0.1 to minimize creative generation.

**Q: Why Qdrant instead of Pinecone or Weaviate?**
A: Qdrant is open-source, Docker-deployable with zero cost, supports multiple named collections (we have 4), has excellent async Python client, and handles payload filtering. For an academic project with multiple modalities needing separate collections, it's the practical choice.

**Q: Why Neo4j instead of a graph library in Python?**
A: Neo4j provides Cypher as a first-class query language for multi-hop traversal, ACID transactions, full-text indexes, and a built-in browser for visualization at localhost:7474 — which I can show right now. A Python library like NetworkX would require loading the entire graph into memory and lacks Cypher's expressiveness for medical ontology queries.

