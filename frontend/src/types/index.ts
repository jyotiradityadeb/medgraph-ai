export interface QueryRequest {
  query: string;
  modalities: string[];
  top_k: number;
  use_graph: boolean;
  graph_depth: number;
  model: string;
}

export interface Source {
  id: string;
  content: string;
  score: number;
  modality: "text" | "image" | "audio" | "table";
  metadata: Record<string, unknown>;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "Drug" | "Disease" | "Symptom" | "Gene" | "LabTest" | string;
  properties: Record<string, string>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  weight: number;
  properties: Record<string, string>;
}

export interface GraphContext {
  nodes: GraphNode[];
  edges: GraphEdge[];
  traversal_depth: number;
  entities_found: string[];
}

export interface StreamMetadata {
  type: "metadata";
  intent: string;
  confidence: number;
  modalities_used: string[];
  graph_nodes_count: number;
  graph_edges_count: number;
  sources_count: number;
  entities_found: string[];
  mode?: "live" | "fallback";
  reason?: string;
  llm_status?: "ok" | "fallback";
}

export interface QueryDoneEvent {
  type: "done";
  processing_time: number;
  llm_status?: "ok" | "fallback";
  sources: Source[];
  graph_context: GraphContext;
}

export interface QueryHistoryItem {
  query: string;
  intent: string;
  processing_time: number;
  sources_count: number;
  graph_nodes: number;
  timestamp: number;
}

export interface HealthStatus {
  status: "ok" | "degraded" | "error";
  services: { qdrant: boolean; neo4j: boolean };
}

export interface MetricsSummary {
  uptime_seconds: number;
  total_queries: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  error_counts: Record<string, number>;
  modality_usage: Record<string, number>;
  avg_graph_nodes: number;
  cache: {
    hits: number;
    misses: number;
    hit_rate: number;
    cached_queries: number;
  };
}

export type NodeType = "Drug" | "Disease" | "Symptom" | "Gene" | "LabTest";

export const NODE_COLORS: Record<string, string> = {
  Drug: "#3B82F6",
  Disease: "#EF4444",
  Symptom: "#F59E0B",
  Gene: "#8B5CF6",
  LabTest: "#10B981",
  default: "#6B7280",
};

export const MODALITY_COLORS: Record<string, string> = {
  text: "#3B82F6",
  image: "#8B5CF6",
  audio: "#10B981",
  table: "#F59E0B",
};
