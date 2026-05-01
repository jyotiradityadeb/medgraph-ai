import { AnimatePresence, motion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";

type QueryStatus = "idle" | "streaming" | "done" | "error";

const STEPS = ["Expanding query", "Vector retrieval", "Graph traversal", "LLM synthesis"];

interface ProcessingTimelineProps {
  status: QueryStatus;
  activeIndex: number;
}

export function ProcessingTimeline({ status, activeIndex }: ProcessingTimelineProps) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Processing Timeline</p>
      <ul className="space-y-2">
        {STEPS.map((step, index) => {
          const done = status === "done" ? true : index < activeIndex;
          const active = status === "streaming" && index === activeIndex;
          return (
            <li key={step} className="flex items-center gap-2 text-sm text-slate-700">
              <AnimatePresence mode="wait">
                {done ? (
                  <motion.span
                    key="done"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-white"
                  >
                    <Check className="h-3 w-3" />
                  </motion.span>
                ) : active ? (
                  <motion.span key="active" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="inline-flex">
                    <Loader2 className="h-5 w-5 animate-spin text-primary" />
                  </motion.span>
                ) : (
                  <motion.span key="idle" className="h-3 w-3 rounded-full bg-slate-300" />
                )}
              </AnimatePresence>
              {step}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
