import { AnimatePresence, motion } from "framer-motion";
import {
  AudioLines,
  ChevronDown,
  FlaskConical,
  Image as ImageIcon,
  Search,
  Table2,
  Text,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import type { Accept } from "react-dropzone";
import toast from "react-hot-toast";

import { useQueryStream } from "@/hooks/useQueryStream";
import type { QueryRequest } from "@/types";

const EXAMPLES = [
  "Warfarin interactions in elderly patients with AF",
  "Interpret: HbA1c 8.9%, BNP 450, eGFR 52",
  "Differential diagnosis: dyspnea + orthopnea + edema",
  "Metformin safety in CKD stage 3b patient",
  "First-line treatment for T2DM with HbA1c 8.5%",
  "How does furosemide cause hypokalemia?",
];

const MODALITY_META = [
  { key: "text", label: "Text", color: "bg-blue-500", icon: Text },
  { key: "image", label: "Image", color: "bg-purple-500", icon: ImageIcon },
  { key: "audio", label: "Audio", color: "bg-emerald-500", icon: AudioLines },
  { key: "table", label: "Table", color: "bg-amber-500", icon: Table2 },
] as const;

export function QueryPanel() {
  const [query, setQuery] = useState("");
  const [modalities, setModalities] = useState<string[]>(["text"]);
  const [graphDepth, setGraphDepth] = useState(2);
  const [topK, setTopK] = useState(5);
  const [useGraph, setUseGraph] = useState(true);
  const [model, setModel] = useState("gpt-4o");
  const [showOptions, setShowOptions] = useState(false);
  const [files, setFiles] = useState<File[]>([]);

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const { submit, reset, status } = useQueryStream();
  const isStreaming = status === "streaming";

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const acceptsMedia = useMemo(() => modalities.includes("image") || modalities.includes("audio"), [modalities]);
  const accept = useMemo<Accept | undefined>(() => {
    const value: Accept = {};
    if (modalities.includes("image")) value["image/*"] = [];
    if (modalities.includes("audio")) {
      value["audio/*"] = [];
      value["video/*"] = [];
    }
    return Object.keys(value).length ? value : undefined;
  }, [modalities]);

  const dropzone = useDropzone({
    accept,
    onDrop: (accepted) => setFiles(accepted),
    disabled: !acceptsMedia,
  });

  const toggleModality = (value: string) => {
    setModalities((prev) => {
      if (prev.includes(value)) {
        if (prev.length === 1) return prev;
        return prev.filter((v) => v !== value);
      }
      return [...prev, value];
    });
  };

  const submitQuery = async () => {
    const trimmed = query.trim();
    if (!trimmed) {
      toast.error("Please enter a clinical query.");
      return;
    }
    const payload: QueryRequest = {
      query: trimmed,
      modalities,
      top_k: topK,
      use_graph: useGraph,
      graph_depth: graphDepth,
      model,
    };
    await submit(payload);
  };

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-700">Clinical Query</h2>
        <button type="button" onClick={reset} className="text-xs text-slate-500 hover:text-slate-700">
          Reset
        </button>
      </div>

      <div className="relative">
        <textarea
          ref={textareaRef}
          rows={7}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
              e.preventDefault();
              void submitQuery();
            }
          }}
          placeholder="Ask a clinical question... (Cmd+Enter to submit)"
          className="w-full resize-y rounded-md border border-slate-300 px-3 py-3 text-sm text-slate-800 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
        {query.length > 0 && (
          <button
            type="button"
            onClick={() => setQuery("")}
            className="absolute right-2 top-2 rounded p-1 text-slate-500 hover:bg-slate-100"
          >
            <X className="h-4 w-4" />
          </button>
        )}
        <span className="absolute bottom-2 right-3 text-xs text-slate-400">{query.length}</span>
      </div>

      <div className="mt-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Modalities</p>
        <div className="flex flex-wrap gap-2">
          {MODALITY_META.map((item) => {
            const Icon = item.icon;
            const active = modalities.includes(item.key);
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => toggleModality(item.key)}
                className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm ${
                  active ? `${item.color} border-transparent text-white` : "border-slate-300 bg-white text-slate-700"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-4">
        <button
          type="button"
          onClick={() => setShowOptions((v) => !v)}
          className="flex w-full items-center justify-between rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700"
        >
          Query Options
          <ChevronDown className={`h-4 w-4 transition ${showOptions ? "rotate-180" : ""}`} />
        </button>
        <AnimatePresence initial={false}>
          {showOptions && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="mt-3 grid gap-3 rounded-md border border-slate-200 p-3 sm:grid-cols-2">
                <label className="text-sm">
                  <span className="mb-1 block text-slate-600">Graph Depth</span>
                  <select
                    value={graphDepth}
                    onChange={(e) => setGraphDepth(Number(e.target.value))}
                    className="w-full rounded-md border border-slate-300 px-2 py-2"
                  >
                    <option value={1}>1</option>
                    <option value={2}>2</option>
                    <option value={3}>3</option>
                  </select>
                </label>
                <label className="text-sm">
                  <span className="mb-1 block text-slate-600">Model</span>
                  <select value={model} onChange={(e) => setModel(e.target.value)} className="w-full rounded-md border border-slate-300 px-2 py-2">
                    <option value="gpt-4o">GPT-4o</option>
                    <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                  </select>
                </label>
                <label className="text-sm sm:col-span-2">
                  <span className="mb-1 block text-slate-600">Top K results: {topK}</span>
                  <input
                    type="range"
                    min={3}
                    max={10}
                    value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                    className="w-full"
                  />
                </label>
                <label className="inline-flex items-center gap-2 text-sm text-slate-700 sm:col-span-2">
                  <input type="checkbox" checked={useGraph} onChange={(e) => setUseGraph(e.target.checked)} />
                  Use graph context
                </label>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="mt-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Example Queries</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setQuery(item)}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-700 hover:border-primary hover:text-primary"
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      {acceptsMedia && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Upload Zone</p>
          <div
            {...dropzone.getRootProps()}
            className={`cursor-pointer rounded-md border border-dashed p-4 text-center ${
              dropzone.isDragActive ? "border-primary bg-blue-50" : "border-slate-300"
            }`}
          >
            <input {...dropzone.getInputProps()} />
            <p className="text-sm text-slate-600">Drop image/audio files or click to select.</p>
            {files.length > 0 && (
              <div className="mt-3 space-y-2">
                {files.map((file) => (
                  <div key={file.name} className="text-xs text-slate-500">
                    {file.type.startsWith("image/") ? (
                      <img src={URL.createObjectURL(file)} alt={file.name} className="mx-auto mb-1 h-20 rounded object-cover" />
                    ) : null}
                    {file.name}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => void submitQuery()}
        disabled={isStreaming}
        className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
      >
        {isStreaming ? (
          <span className="inline-flex items-center gap-2">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            Streaming...
          </span>
        ) : (
          <>
            <Search className="h-4 w-4" />
            Analyze Query
          </>
        )}
      </button>
    </section>
  );
}
