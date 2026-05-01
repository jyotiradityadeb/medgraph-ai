import forceAtlas2 from "graphology-layout-forceatlas2";
import Graph from "graphology";
import Sigma from "sigma";
import { useEffect, useMemo, useRef, useState } from "react";

import { useQueryStore } from "@/store/queryStore";
import { NODE_COLORS, type GraphEdge, type GraphNode } from "@/types";

import { GraphControls } from "./GraphControls";

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

function nodeSize(type: string): number {
  if (type === "Disease") return 16;
  if (type === "Drug") return 14;
  if (type === "LabTest") return 12;
  if (type === "Gene") return 10;
  if (type === "Symptom") return 10;
  return 10;
}

function edgeColorByType(relationship: string): string {
  const rel = relationship.toUpperCase();
  if (rel.includes("TREATS")) return "#1D9E75";
  if (rel.includes("INTERACTS")) return "#D97706";
  if (rel.includes("CONTRAINDICATED")) return "#DC2626";
  if (rel.includes("CAUSES")) return "#DC2626";
  if (rel.includes("DIAGNOSED")) return "#8B5CF6";
  return "#94A3B8";
}

export function GraphCanvas({ nodes, edges }: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const setSelectedNode = useQueryStore((s) => s.setSelectedNode);

  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  const nodeMap = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const graph = new Graph();
    const timeouts: number[] = [];

    nodes.forEach((node, index) => {
      const t = window.setTimeout(() => {
        if (!graph.hasNode(node.id)) {
          graph.addNode(node.id, {
            x: Math.random(),
            y: Math.random(),
            size: nodeSize(node.type),
            color: NODE_COLORS[node.type] || NODE_COLORS.default,
            label: node.label,
          });
        }
      }, index * 30);
      timeouts.push(t);
    });

    const edgeStartDelay = nodes.length * 30 + 50;
    edges.forEach((edge, index) => {
      const t = window.setTimeout(() => {
        if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target)) return;
        const key = `${edge.source}-${edge.relationship}-${edge.target}-${index}`;
        if (!graph.hasEdge(key)) {
          graph.addDirectedEdgeWithKey(key, edge.source, edge.target, {
            size: 1.5,
            color: edgeColorByType(edge.relationship),
          });
        }
      }, edgeStartDelay + index * 30);
      timeouts.push(t);
    });

    const layoutTimer = window.setTimeout(() => {
      if (graph.order > 0) forceAtlas2.assign(graph, { iterations: 150 });
      const renderer = new Sigma(graph, container, {
        renderEdgeLabels: false,
        defaultEdgeType: "arrow",
        labelSize: 11,
      });
      sigmaRef.current = renderer;

      renderer.on("enterNode", ({ node }) => setHoveredNodeId(String(node)));
      renderer.on("leaveNode", () => setHoveredNodeId(null));
      renderer.on("clickNode", ({ node }) => {
        const found = nodeMap.get(String(node));
        if (found) setSelectedNode(found);
      });
    }, edgeStartDelay + edges.length * 30 + 80);
    timeouts.push(layoutTimer);

    return () => {
      for (const t of timeouts) window.clearTimeout(t);
      setHoveredNodeId(null);
      if (sigmaRef.current) {
        sigmaRef.current.kill();
        sigmaRef.current = null;
      }
      container.innerHTML = "";
    };
  }, [edges, nodeMap, nodes, setSelectedNode]);

  const zoomIn = () => {
    const renderer = sigmaRef.current;
    if (!renderer) return;
    const camera = renderer.getCamera();
    camera.animate({ ratio: camera.getState().ratio / 1.25 }, { duration: 200 });
  };

  const zoomOut = () => {
    const renderer = sigmaRef.current;
    if (!renderer) return;
    const camera = renderer.getCamera();
    camera.animate({ ratio: camera.getState().ratio * 1.25 }, { duration: 200 });
  };

  const resetCamera = () => {
    const renderer = sigmaRef.current;
    if (!renderer) return;
    renderer.getCamera().animatedReset();
  };

  const fullscreen = () => {
    const el = containerRef.current;
    if (!el) return;
    void el.requestFullscreen?.();
  };

  return (
    <div className="relative h-full min-h-[560px] overflow-hidden rounded-lg border border-slate-200 bg-white">
      <GraphControls onZoomIn={zoomIn} onZoomOut={zoomOut} onReset={resetCamera} onFullscreen={fullscreen} />
      {hoveredNodeId && (
        <div className="absolute left-3 top-3 z-10 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600 shadow-sm">
          {nodeMap.get(hoveredNodeId)?.label || hoveredNodeId}
        </div>
      )}
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}
