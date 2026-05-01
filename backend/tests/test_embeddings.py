from app.core.embeddings import TableEmbedder, TextEmbedder


class TestTextEmbedder:
    def test_embed_returns_correct_shape(self):
        embedder = TextEmbedder()
        result = embedder.embed("Patient has hypertension and diabetes")
        assert isinstance(result, list)
        assert len(result) == 384
        assert all(isinstance(x, float) for x in result)

    def test_embed_batch(self):
        embedder = TextEmbedder()
        texts = ["Text one about aspirin", "Text two about metformin", "Text three about warfarin"]
        results = embedder.embed_batch(texts)
        assert len(results) == 3
        assert all(len(r) == 384 for r in results)

    def test_embed_long_text_no_error(self):
        embedder = TextEmbedder()
        long_text = "patient " * 600
        result = embedder.embed(long_text)
        assert len(result) == 384

    def test_chunk_text_produces_chunks(self):
        embedder = TextEmbedder()
        text = " ".join([f"word{i}" for i in range(1000)])
        chunks = embedder.chunk_text(text, chunk_size=400, overlap=50)
        assert len(chunks) > 1
        assert all(len(c.split()) <= 400 for c in chunks)


class TestTableEmbedder:
    def test_normal_labs_no_abnormal(self):
        embedder = TableEmbedder()
        labs = {"HbA1c": 5.2, "eGFR": 75, "potassium": 4.0}
        vector, abnormal = embedder.embed_lab_values(labs)
        assert len(vector) == 384
        assert len(abnormal) == 0

    def test_abnormal_labs_detected(self):
        embedder = TableEmbedder()
        labs = {"HbA1c": 9.5, "eGFR": 25, "potassium": 6.2}
        vector, abnormal = embedder.embed_lab_values(labs)
        assert len(abnormal) == 3
        statuses = [a["status"] for a in abnormal]
        assert "HIGH" in statuses

    def test_unknown_labs_embedded_without_error(self):
        embedder = TableEmbedder()
        labs = {"random_lab_xyz": 42.0}
        vector, abnormal = embedder.embed_lab_values(labs)
        assert len(vector) == 384
