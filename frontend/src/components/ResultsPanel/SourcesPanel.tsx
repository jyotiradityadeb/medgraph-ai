import * as Dialog from "@radix-ui/react-dialog";
import { AudioLines, FileText, Image as ImageIcon, Table2, X } from "lucide-react";
import { useMemo, useState } from "react";

import { MODALITY_COLORS, type Source } from "@/types";

interface SourcesPanelProps {
  sources: Source[];
}

function iconForModality(modality: Source["modality"]) {
  if (modality === "image") return ImageIcon;
  if (modality === "audio") return AudioLines;
  if (modality === "table") return Table2;
  return FileText;
}

export function SourcesPanel({ sources }: SourcesPanelProps) {
  const [openSource, setOpenSource] = useState<Source | null>(null);

  const cards = useMemo(() => sources.slice(0, 10), [sources]);

  if (!cards.length) return null;

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sources</p>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {cards.map((source) => {
          const Icon = iconForModality(source.modality);
          const scorePercent = Math.max(0, Math.min(100, Math.round(source.score * 100)));
          return (
            <button
              key={`${source.modality}-${source.id}`}
              type="button"
              onClick={() => setOpenSource(source)}
              className="w-[200px] shrink-0 rounded-md border border-slate-200 bg-white p-3 text-left"
            >
              <div className="mb-2 h-1 rounded" style={{ backgroundColor: MODALITY_COLORS[source.modality] || "#6B7280" }} />
              <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
                <span className="inline-flex items-center gap-1">
                  <Icon className="h-3.5 w-3.5" />
                  {source.modality}
                </span>
                <span>{scorePercent}%</span>
              </div>
              <div className="mb-2 h-1.5 rounded-full bg-slate-200">
                <div className="h-full rounded-full bg-primary" style={{ width: `${scorePercent}%` }} />
              </div>
              <p className="h-[4.5rem] overflow-hidden text-xs leading-5 text-slate-700">{source.content}</p>
            </button>
          );
        })}
      </div>

      <Dialog.Root open={Boolean(openSource)} onOpenChange={(open: boolean) => !open && setOpenSource(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-900/40" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(720px,92vw)] -translate-x-1/2 -translate-y-1/2 rounded-md border border-slate-200 bg-white p-4 shadow-xl">
            <div className="mb-3 flex items-center justify-between">
              <Dialog.Title className="text-sm font-semibold text-slate-800">Source Detail</Dialog.Title>
              <Dialog.Close asChild>
                <button type="button" className="rounded p-1 text-slate-500 hover:bg-slate-100">
                  <X className="h-4 w-4" />
                </button>
              </Dialog.Close>
            </div>
            <div className="max-h-[60vh] overflow-y-auto rounded border border-slate-200 bg-slate-50 p-3">
              <pre className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{openSource?.content || ""}</pre>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
