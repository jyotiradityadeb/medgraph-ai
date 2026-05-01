import { Activity, Database, Network, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { useQueryStore } from "@/store/queryStore";

import { ProcessingTimeline } from "./ProcessingTimeline";
import { SourcesPanel } from "./SourcesPanel";
import { StreamingAnswer } from "./StreamingAnswer";

const EMPTY_FEATURES = [
  { icon: Activity, title: "Intent Analysis", description: "Classifies clinical request complexity and modality needs." },
  { icon: Database, title: "Multi-modal Retrieval", description: "Fuses text, image, audio, and lab-table evidence." },
  { icon: Network, title: "Graph Traversal", description: "Traverses medical relationships for multi-hop reasoning." },
  { icon: ShieldCheck, title: "Clinical Safeguards", description: "Flags interactions, contraindications, and critical values." },
];

export function ResultsPanel() {
  const answer = useQueryStore((s) => s.currentAnswer);
  const status = useQueryStore((s) => s.streamStatus);
  const metadata = useQueryStore((s) => s.metadata);
  const sources = useQueryStore((s) => s.sources);

  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    if (status !== "streaming") return;
    setActiveStep(0);
    const timer = window.setInterval(() => {
      setActiveStep((prev) => Math.min(prev + 1, 3));
    }, 900);
    return () => window.clearInterval(timer);
  }, [status]);

  if (status === "idle" && answer.length === 0) {
    return (
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Results</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {EMPTY_FEATURES.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.title} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <Icon className="mb-2 h-4 w-4 text-primary" />
                <p className="text-sm font-medium text-slate-700">{item.title}</p>
                <p className="mt-1 text-xs text-slate-500">{item.description}</p>
              </div>
            );
          })}
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-700">Results</h2>

      {(status === "streaming" || (status === "done" && answer.length > 0)) && (
        <ProcessingTimeline status={status} activeIndex={status === "done" ? 3 : activeStep} />
      )}

      {(answer.length > 0 || metadata) && <StreamingAnswer answer={answer} metadata={metadata} />}

      <SourcesPanel sources={sources} />
    </section>
  );
}
