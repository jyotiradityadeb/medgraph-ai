import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { StreamMetadata } from "@/types";

interface StreamingAnswerProps {
  answer: string;
  metadata: StreamMetadata | null;
}

function intentColor(intent: string): string {
  const map: Record<string, string> = {
    drug_interaction: "bg-amber-100 text-amber-700",
    diagnosis: "bg-blue-100 text-blue-700",
    treatment: "bg-emerald-100 text-emerald-700",
    lab_interpretation: "bg-purple-100 text-purple-700",
    symptom_lookup: "bg-orange-100 text-orange-700",
    pharmacology: "bg-indigo-100 text-indigo-700",
    general: "bg-slate-100 text-slate-700",
  };
  return map[intent] || "bg-slate-100 text-slate-700";
}

export function StreamingAnswer({ answer, metadata }: StreamingAnswerProps) {
  const confidencePct = Math.round((metadata?.confidence ?? 0) * 100);
  const isFallback = metadata?.mode === "fallback" || metadata?.llm_status === "fallback";

  return (
    <div className="space-y-3">
      {metadata && (
        <div className="space-y-2 rounded-md border border-slate-200 bg-slate-50 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-2 py-1 text-xs font-medium ${intentColor(metadata.intent)}`}>
              {metadata.intent}
            </span>
            {isFallback && (
              <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700">
                Fallback Mode
              </span>
            )}
            <span className="rounded-full bg-slate-200 px-2 py-1 text-xs text-slate-700">
              {metadata.graph_nodes_count} graph nodes
            </span>
            {metadata.modalities_used.map((modality) => (
              <span key={modality} className="rounded-full border border-slate-300 bg-white px-2 py-1 text-xs text-slate-600">
                {modality}
              </span>
            ))}
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
              <span>Confidence</span>
              <span>{confidencePct}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-200">
              <div className="h-full bg-primary transition-all" style={{ width: `${confidencePct}%` }} />
            </div>
          </div>
        </div>
      )}

      {isFallback && (
        <div
          style={{
            background: "#FAEEDA",
            border: "1px solid #BA7517",
            padding: "8px 12px",
            borderRadius: "6px",
            marginBottom: "12px",
          }}
        >
          ⚠️ AI synthesis unavailable. Showing structured evidence summary only.
        </div>
      )}

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="prose prose-sm max-w-none text-slate-700 [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:tracking-wide [&_h2]:text-slate-900 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:text-slate-900 [&_ul]:pl-4 [&_li]:leading-6 [&_p]:leading-6"
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
      </motion.div>
    </div>
  );
}
