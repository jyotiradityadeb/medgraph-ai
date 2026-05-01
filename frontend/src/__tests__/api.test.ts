import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";

describe("api client", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("api.health() calls correct URL", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok", services: { qdrant: true, neo4j: true } }),
    });

    await api.health();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/health");
  });

  it("api.query.stream() sends POST with correct body", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      headers: new Headers({ "content-type": "text/event-stream" }),
      body: null,
    });

    const payload = {
      query: "What is hypertension?",
      modalities: ["text"],
      top_k: 3,
      use_graph: false,
      graph_depth: 1,
      model: "gpt-4o",
    };

    await api.query.stream(payload);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/query",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    );
  });

  it("api.ingest.text() sends correct JSON", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ document_id: "abc123", success: true }),
    });

    await api.ingest.text("test clinical content", "unit_test_source", { test: true });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/ingest/text",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: "test clinical content",
          source: "unit_test_source",
          metadata: { test: true },
        }),
      })
    );
  });
});

