import { NODE_COLORS, type GraphEdge } from "@/types";

interface GraphLegendProps {
  edges: GraphEdge[];
}

function colorForRelationship(rel: string): string {
  const bucket = rel.toUpperCase();
  if (bucket.includes("TREATS")) return "#1D9E75";
  if (bucket.includes("INTERACTS")) return "#D97706";
  if (bucket.includes("CONTRAINDICATED")) return "#DC2626";
  if (bucket.includes("CAUSES")) return "#DC2626";
  if (bucket.includes("DIAGNOSED")) return "#8B5CF6";
  return "#64748B";
}

export function GraphLegend({ edges }: GraphLegendProps) {
  const relationshipTypes = Array.from(new Set(edges.map((e) => e.relationship))).slice(0, 8);

  return (
    <div className="rounded-md border border-slate-200 bg-white/95 p-3 text-xs text-slate-600 shadow-sm backdrop-blur">
      <p className="mb-2 font-semibold text-slate-700">Node Types</p>
      <div className="grid grid-cols-2 gap-2">
        {Object.entries(NODE_COLORS)
          .filter(([key]) => key !== "default")
          .map(([key, color]) => (
            <div key={key} className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
              {key}
            </div>
          ))}
      </div>
      <p className="mb-2 mt-3 font-semibold text-slate-700">Relationships</p>
      <div className="space-y-1.5">
        {relationshipTypes.length === 0 ? (
          <p className="text-slate-400">No edges loaded</p>
        ) : (
          relationshipTypes.map((type) => (
            <div key={type} className="flex items-center gap-2">
              <span className="h-[2px] w-4" style={{ backgroundColor: colorForRelationship(type) }} />
              <span className="max-w-[160px] truncate">{type}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
