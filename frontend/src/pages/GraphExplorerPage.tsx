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

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      if (!query.trim()) return;
      setLoading(true);
      try {
        const result = await api.graph.explore(query.trim(), depth);
        setNodes(result.nodes);
        setEdges(result.edges);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Failed to explore graph");
      } finally {
        setLoading(false);
      }
    }, 500);

    return () => window.clearTimeout(timer);
  }, [depth, query]);

  const statsText = useMemo(() => `${nodes.length} nodes, ${edges.length} edges`, [edges.length, nodes.length]);

  const onExploreFromNode = async (node: GraphNode) => {
    try {
      setLoading(true);
      const result = await api.graph.explore(node.label, depth);
      setNodes(result.nodes);
      setEdges(result.edges);
      setSelectedNode(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to explore node");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-white p-3">
        <div className="relative min-w-[280px] flex-1">
          <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search graph entity..."
            className="w-full rounded-md border border-slate-300 py-2 pl-8 pr-3 text-sm outline-none focus:border-primary"
          />
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
