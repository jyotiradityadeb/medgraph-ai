from typing import Any

from pydantic import BaseModel, Field


class Source(BaseModel):
    id: str
    content: str
    score: float
    modality: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    weight: float = 1.0
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphContext(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    traversal_depth: int
    entities_found: list[str]


class QueryRequest(BaseModel):
    query: str
    modalities: list[str] = Field(default_factory=lambda: ["text"])
    top_k: int = 5
    use_graph: bool = True
    graph_depth: int = 2
    model: str = "gpt-4o"


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
    graph_context: GraphContext
    processing_time: float
    confidence: float
    intent: str
    modalities_used: list[str]


class IngestRequest(BaseModel):
    content: str
    source: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    success: bool
    document_id: str
    message: str
    entities_found: list[str] = Field(default_factory=list)


class QueryIntent(BaseModel):
    intent: str
    relevant_modalities: list[str]
    extracted_entities: dict[str, Any]
    complexity: str
    requires_graph: bool
