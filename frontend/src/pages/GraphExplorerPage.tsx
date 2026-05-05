import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";

import { api } from "@/api/client";
import { GraphCanvas } from "@/components/GraphVisualization/GraphCanvas";
import { GraphLegend } from "@/components/GraphVisualization/GraphLegend";
import { NodeDetailPanel } from "@/components/GraphVisualization/NodeDetailPanel";
import { useQueryStore } from "@/store/queryStore";
import type { GraphEdge, GraphNode } from "@/types";

export function GraphExplorerPage() {
  const selectedNode = useQueryStore((s) => s.selectedNode);
  const setSelectedNode = useQueryStore((s) => s.setSelectedNode);

  const [query, setQuery] = useState("heart failure");
  const [depth, setDepth] = useState(2);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<GraphNode[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      const q = query.trim();
      if (!q) {
        setSearchResults([]);
        setHasSearched(false);
        return;
      }
      try {
        const result = await api.graph.search(q);
        setSearchResults(result.results);
        setHasSearched(true);
        setShowResults(true);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Failed to search graph");
      }
    }, 500);

    return () => window.clearTimeout(timer);
  }, [query]);

  const statsText = useMemo(() => `${nodes.length} nodes, ${edges.length} edges`, [edges.length, nodes.length]);

  const exploreEntity = async (entityLabel: string) => {
    try {
      setLoading(true);
      const result = await api.graph.explore(entityLabel, depth);
      setNodes(result.nodes);
      setEdges(result.edges);
      setShowResults(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to explore graph");
    } finally {
      setLoading(false);
    }
  };

  const onExploreFromNode = async (node: GraphNode) => {
    try {
      setLoading(true);
      await exploreEntity(node.label);
      setSelectedNode(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to explore node");
    }
  };

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-white p-3">
        <div className="relative min-w-[280px] flex-1">
          <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setShowResults(true);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                const q = query.trim();
                if (q) void exploreEntity(q);
              }
            }}
            placeholder="Search graph entity..."
            className="w-full rounded-md border border-slate-300 py-2 pl-8 pr-3 text-sm outline-none focus:border-primary"
          />
          {showResults && hasSearched && (
            <div className="absolute left-0 right-0 top-[calc(100%+6px)] z-20 max-h-56 overflow-y-auto rounded-md border border-slate-200 bg-white shadow-lg">
              {searchResults.length === 0 ? (
                <p className="px-3 py-2 text-xs text-slate-500">
                  No entities found. Try: Warfarin, Diabetes, Dyspnea, TSH, CYP2C9
                </p>
              ) : (
                searchResults.map((item) => (
                  <button
                    key={`${item.type}-${item.id}`}
                    type="button"
                    onClick={() => void exploreEntity(item.label)}
                    className="block w-full border-b border-slate-100 px-3 py-2 text-left text-sm text-slate-700 last:border-b-0 hover:bg-slate-50"
                  >
                    <span className="font-medium">{item.label}</span>
                    <span className="ml-2 text-xs text-slate-500">{item.type}</span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
        <select value={depth} onChange={(e) => setDepth(Number(e.target.value))} className="rounded-md border border-slate-300 px-2 py-2 text-sm">
          <option value={1}>Depth 1</option>
          <option value={2}>Depth 2</option>
          <option value={3}>Depth 3</option>
        </select>
        <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-600">{loading ? "Loading..." : statsText}</span>
      </div>

      <div className="relative">
        <GraphCanvas nodes={nodes} edges={edges} />
        <div className="absolute bottom-3 left-3">
          <GraphLegend edges={edges} />
        </div>
        <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} onExplore={onExploreFromNode} />
      </div>
    </section>
  );
}
