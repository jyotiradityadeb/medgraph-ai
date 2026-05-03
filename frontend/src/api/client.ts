import type {
  GraphEdge,
  GraphNode,
  HealthStatus,
  MetricsSummary,
  QueryHistoryItem,
  QueryRequest,
} from "@/types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY as string | undefined;

function authHeaders(): Record<string, string> {
  return API_KEY ? { "X-API-Key": API_KEY } : {};
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(API_BASE + path, { headers: authHeaders() });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

async function postForm<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<HealthStatus>("/health"),
  metrics: () => get<MetricsSummary>("/api/v1/metrics"),
  query: {
    stream: (request: QueryRequest, signal?: AbortSignal): Promise<Response> =>
      fetch(API_BASE + "/api/v1/query", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(request),
        signal,
      }),
    history: () => get<{ history: QueryHistoryItem[] }>("/api/v1/query/history"),
  },
  graph: {
    explore: (entity: string, depth = 2) =>
      get<{ nodes: GraphNode[]; edges: GraphEdge[]; stats: { node_count: number; edge_count: number } }>(
        `/api/v1/graph/explore?entity=${encodeURIComponent(entity)}&depth=${depth}`
      ),
    stats: () => get<Record<string, number>>("/api/v1/graph/stats"),
    search: (q: string) => get<{ results: GraphNode[] }>(`/api/v1/graph/search?q=${encodeURIComponent(q)}`),
  },
  ingest: {
    text: (content: string, source = "", metadata = {}) =>
      post<{ document_id: string; success: boolean; entities_found?: string[] }>("/api/v1/ingest/text", { content, source, metadata }),
    image: (file: File, metadata = {}) => {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("metadata", JSON.stringify(metadata));
      return postForm<{ document_id: string; description: string }>("/api/v1/ingest/image", fd);
    },
    audio: (file: File, metadata = {}) => {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("metadata", JSON.stringify(metadata));
      return postForm<{ document_id: string; transcript: string }>("/api/v1/ingest/audio", fd);
    },
    pdf: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return postForm<{ document_id: string; pages: number; success: boolean }>("/api/v1/ingest/pdf", fd);
    },
    table: (labValues: Record<string, number>, patientId = "") =>
      post<{ document_id: string; abnormal_values: unknown[] }>("/api/v1/ingest/table", {
        lab_values: labValues,
        patient_id: patientId,
      }),
  },
};
