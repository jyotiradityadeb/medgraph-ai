import pytest

pytestmark = pytest.mark.asyncio


class TestHealth:
    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ["ok", "degraded"]
        assert "services" in data
        assert "qdrant" in data["services"]
        assert "neo4j" in data["services"]


class TestGraphEndpoints:
    async def test_graph_stats(self, client):
        resp = await client.get("/api/v1/graph/stats")
        assert resp.status_code == 200

    async def test_graph_explore_returns_structure(self, client):
        resp = await client.get("/api/v1/graph/explore?entity=Aspirin&depth=1")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data

    async def test_graph_explore_unknown_entity(self, client):
        resp = await client.get("/api/v1/graph/explore?entity=NotADrug12345&depth=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["nodes"] == []

    async def test_graph_search(self, client):
        resp = await client.get("/api/v1/graph/search?q=warfarin")
        assert resp.status_code == 200


class TestIngestEndpoints:
    async def test_ingest_text(self, client):
        resp = await client.post(
            "/api/v1/ingest/text",
            json={
                "content": "Patient has hypertension managed with lisinopril 10mg daily. Blood pressure 138/82.",
                "source": "test_note",
                "metadata": {"test": True},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "document_id" in data
        assert len(data["document_id"]) > 0

    async def test_ingest_lab_table(self, client):
        resp = await client.post(
            "/api/v1/ingest/table",
            json={
                "lab_values": {"HbA1c": 8.5, "eGFR": 55, "potassium": 4.2},
                "patient_id": "test_patient_001",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "abnormal_values" in data
        abnormal_names = [a["test"] for a in data["abnormal_values"]]
        assert "HbA1c" in abnormal_names


class TestQueryEndpoints:
    async def test_query_returns_streaming_response(self, client):
        resp = await client.post(
            "/api/v1/query",
            json={
                "query": "What is hypertension?",
                "modalities": ["text"],
                "top_k": 3,
                "use_graph": False,
                "graph_depth": 1,
                "model": "gpt-4o",
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    async def test_query_history_endpoint(self, client):
        resp = await client.get("/api/v1/query/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "history" in data
        assert isinstance(data["history"], list)

    async def test_query_with_invalid_model_still_responds(self, client):
        resp = await client.post(
            "/api/v1/query",
            json={
                "query": "test",
                "modalities": ["text"],
                "top_k": 3,
                "use_graph": False,
                "graph_depth": 1,
                "model": "gpt-3.5-turbo",
            },
        )
        assert resp.status_code in [200, 422, 500]


class TestMetrics:
    async def test_metrics_endpoint(self, client):
        resp = await client.get("/api/v1/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_queries" in data
