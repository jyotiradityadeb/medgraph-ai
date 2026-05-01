import { AnimatePresence, motion } from "framer-motion";

import type { GraphNode } from "@/types";

interface NodeDetailPanelProps {
  node: GraphNode | null;
  onClose: () => void;
  onExplore: (node: GraphNode) => void;
}

const TYPE_BADGE: Record<string, string> = {
  Drug: "bg-blue-100 text-blue-700",
  Disease: "bg-red-100 text-red-700",
  Symptom: "bg-amber-100 text-amber-700",
  Gene: "bg-purple-100 text-purple-700",
  LabTest: "bg-emerald-100 text-emerald-700",
};

export function NodeDetailPanel({ node, onClose, onExplore }: NodeDetailPanelProps) {
  return (
    <AnimatePresence>
      {node && (
        <motion.aside
          initial={{ x: 360, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 360, opacity: 0 }}
          className="absolute right-0 top-0 z-20 h-full w-[320px] border-l border-slate-200 bg-white p-4 shadow-xl"
        >
          <div className="mb-3 flex items-start justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">{node.label}</h2>
              <span className={`mt-1 inline-block rounded-full px-2 py-1 text-xs font-medium ${TYPE_BADGE[node.type] || "bg-slate-100 text-slate-700"}`}>
                {node.type}
              </span>
            </div>
            <button type="button" onClick={onClose} className="text-sm text-slate-500 hover:text-slate-700">
              Close
            </button>
          </div>

          <div className="max-h-[62vh] overflow-y-auto rounded-md border border-slate-200">
            <table className="w-full text-left text-xs">
              <tbody>
                {Object.entries(node.properties).map(([key, value]) => (
                  <tr key={key} className="border-b border-slate-100">
                    <td className="w-1/3 bg-slate-50 px-2 py-1.5 font-medium text-slate-600">{key}</td>
                    <td className="px-2 py-1.5 text-slate-700">{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button
            type="button"
            onClick={() => onExplore(node)}
            className="mt-3 w-full rounded-md bg-primary px-3 py-2 text-sm font-medium text-white"
          >
            Explore from this node
          </button>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
