import { motion } from "framer-motion";

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

function renderLine(line: string, index: number) {
  if (line.startsWith("## ")) {
    return (
      <h3 key={index} className="pt-2 text-sm font-semibold tracking-wide text-slate-900">
        {line.replace(/^##\s+/, "")}
      </h3>
    );
  }

  if (line.startsWith("INTERACTION WARNING:")) {
    return (
      <div key={index} className="rounded-md border border-amber-300 bg-amber-50 p-2 text-amber-800">
        {line}
      </div>
    );
  }

  if (line.startsWith("CONTRAINDICATION:")) {
    return (
      <div key={index} className="rounded-md border border-red-300 bg-red-50 p-2 text-red-800">
        {line}
      </div>
    );
  }

  if (line.startsWith("CRITICAL VALUE:")) {
    return (
      <div key={index} className="rounded-md border border-red-500 bg-red-100 p-2 font-medium text-red-900">
        {line}
      </div>
    );
  }

  const withCitations = line.split(/(\[Doc\s+\d+\])/g);
  return (
    <p key={index} className="text-sm leading-6 text-slate-700">
      {withCitations.map((part, idx) =>
        /\[Doc\s+\d+\]/.test(part) ? (
          <sup
            key={`${part}-${idx}`}
            className="mx-0.5 cursor-pointer rounded border border-primary/30 bg-primary/10 px-1 text-[10px] font-medium text-primary"
          >
            {part}
          </sup>
        ) : (
          <span key={`${part}-${idx}`}>{part}</span>
        )
      )}
    </p>
  );
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
            <span className="rounded-full bg-slate-200 px-2 py-1 text-xs text-slate-700">{metadata.graph_nodes_count} graph nodes</span>
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
        <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          ⚠️ AI synthesis unavailable. Showing structured evidence summary only.
        </div>
      )}

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-2">
        {answer
          .split("\n")
          .filter((line) => line.trim().length > 0)
          .map((line, index) => renderLine(line, index))}
      </motion.div>
    </div>
  );
}
