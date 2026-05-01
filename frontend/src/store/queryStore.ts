import { create } from "zustand";

import type { GraphContext, GraphNode, QueryHistoryItem, Source, StreamMetadata } from "@/types";

interface QueryStore {
  currentAnswer: string;
  setCurrentAnswer: (a: string) => void;
  appendToAnswer: (chunk: string) => void;

  streamStatus: "idle" | "streaming" | "done" | "error";
  setStreamStatus: (s: QueryStore["streamStatus"]) => void;

  metadata: StreamMetadata | null;
  setMetadata: (m: StreamMetadata) => void;

  sources: Source[];
  setSources: (s: Source[]) => void;

  graphContext: GraphContext | null;
  setGraphContext: (g: GraphContext) => void;

  selectedNode: GraphNode | null;
  setSelectedNode: (n: GraphNode | null) => void;

  processingTime: number;
  setProcessingTime: (t: number) => void;

  resetQuery: () => void;

  queryHistory: QueryHistoryItem[];
  addToHistory: (item: QueryHistoryItem) => void;
}

export const useQueryStore = create<QueryStore>((set) => ({
  currentAnswer: "",
  setCurrentAnswer: (a) => set({ currentAnswer: a }),
  appendToAnswer: (chunk) => set((state) => ({ currentAnswer: state.currentAnswer + chunk })),

  streamStatus: "idle",
  setStreamStatus: (s) => set({ streamStatus: s }),

  metadata: null,
  setMetadata: (m) => set({ metadata: m }),

  sources: [],
  setSources: (s) => set({ sources: s }),

  graphContext: null,
  setGraphContext: (g) => set({ graphContext: g }),

  selectedNode: null,
  setSelectedNode: (n) => set({ selectedNode: n }),

  processingTime: 0,
  setProcessingTime: (t) => set({ processingTime: t }),

  resetQuery: () =>
    set({
      currentAnswer: "",
      streamStatus: "idle",
      metadata: null,
      sources: [],
      graphContext: null,
      processingTime: 0,
    }),

  queryHistory: [],
  addToHistory: (item) =>
    set((state) => {
      const next = [item, ...state.queryHistory];
      return { queryHistory: next.slice(0, 50) };
    }),
}));

export type { QueryStore };
