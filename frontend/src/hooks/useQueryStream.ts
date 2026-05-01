import { useCallback, useRef } from "react";
import toast from "react-hot-toast";

import { api } from "@/api/client";
import { useQueryStore } from "@/store/queryStore";
import type { QueryDoneEvent, QueryRequest, Source, StreamMetadata } from "@/types";

type StreamChunkEvent = { type: "chunk"; content: string };
type StreamErrorEvent = { type: "error"; message: string };
type StreamEvent = StreamMetadata | StreamChunkEvent | QueryDoneEvent | StreamErrorEvent;

function parseSseBuffer(buffer: string): { events: StreamEvent[]; rest: string } {
  const normalized = buffer.replace(/\r\n/g, "\n");
  const chunks = normalized.split("\n\n");
  const rest = chunks.pop() ?? "";
  const events: StreamEvent[] = [];

  for (const chunk of chunks) {
    const dataLines = chunk
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .filter(Boolean);

    const payload = dataLines.join("\n");
    if (!payload) continue;

    try {
      const parsed = JSON.parse(payload) as StreamEvent;
      events.push(parsed);
    } catch {
      continue;
    }
  }

  return { events, rest };
}

export function useQueryStream() {
  const controllerRef = useRef<AbortController | null>(null);
  const streamStatus = useQueryStore((s) => s.streamStatus);
  const setCurrentAnswer = useQueryStore((s) => s.setCurrentAnswer);
  const appendToAnswer = useQueryStore((s) => s.appendToAnswer);
  const setStreamStatus = useQueryStore((s) => s.setStreamStatus);
  const setMetadata = useQueryStore((s) => s.setMetadata);
  const setSources = useQueryStore((s) => s.setSources);
  const setGraphContext = useQueryStore((s) => s.setGraphContext);
  const setProcessingTime = useQueryStore((s) => s.setProcessingTime);
  const resetQueryStore = useQueryStore((s) => s.resetQuery);
  const addToHistory = useQueryStore((s) => s.addToHistory);

  const reset = useCallback(() => {
    if (controllerRef.current) {
      controllerRef.current.abort();
      controllerRef.current = null;
    }
    resetQueryStore();
  }, [resetQueryStore]);

  const submit = useCallback(
    async (request: QueryRequest) => {
      if (controllerRef.current) {
        controllerRef.current.abort();
      }
      const controller = new AbortController();
      controllerRef.current = controller;

      resetQueryStore();
      setCurrentAnswer("");
      setStreamStatus("streaming");

      try {
        const response = await api.query.stream(request, controller.signal);

        if (!response.ok) {
          throw new Error(`API error ${response.status}: ${await response.text()}`);
        }
        if (!response.body) {
          throw new Error("Empty stream response body.");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let pending = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) {
            pending += decoder.decode();
            break;
          }

          pending += decoder.decode(value, { stream: true });
          const parsed = parseSseBuffer(pending);
          pending = parsed.rest;

          for (const event of parsed.events) {
            if (event.type === "metadata") {
              setMetadata(event);
            } else if (event.type === "chunk") {
              appendToAnswer(event.content);
            } else if (event.type === "done") {
              setSources(event.sources as Source[]);
              setGraphContext(event.graph_context);
              setProcessingTime(event.processing_time);
              setStreamStatus("done");
              addToHistory({
                query: request.query,
                intent: useQueryStore.getState().metadata?.intent ?? "general",
                processing_time: event.processing_time,
                sources_count: event.sources.length,
                graph_nodes: event.graph_context.nodes.length,
                timestamp: Date.now() / 1000,
              });
            } else if (event.type === "error") {
              setStreamStatus("error");
              toast.error(event.message || "Query failed.");
            }
          }
        }

        if (pending.trim().length > 0) {
          const finalParsed = parseSseBuffer(`${pending}\n\n`);
          for (const event of finalParsed.events) {
            if (event.type === "metadata") {
              setMetadata(event);
            } else if (event.type === "chunk") {
              appendToAnswer(event.content);
            } else if (event.type === "done") {
              setSources(event.sources as Source[]);
              setGraphContext(event.graph_context);
              setProcessingTime(event.processing_time);
              setStreamStatus("done");
              addToHistory({
                query: request.query,
                intent: useQueryStore.getState().metadata?.intent ?? "general",
                processing_time: event.processing_time,
                sources_count: event.sources.length,
                graph_nodes: event.graph_context.nodes.length,
                timestamp: Date.now() / 1000,
              });
            } else if (event.type === "error") {
              setStreamStatus("error");
              toast.error(event.message || "Query failed.");
            }
          }
        }

        if (useQueryStore.getState().streamStatus === "streaming") {
          setStreamStatus("done");
        }
      } catch (error) {
        if (controller.signal.aborted) {
          setStreamStatus("idle");
          return;
        }
        const message = error instanceof Error ? error.message : "Unknown network error.";
        setStreamStatus("error");
        toast.error(message);
      } finally {
        if (controllerRef.current === controller) {
          controllerRef.current = null;
        }
      }
    },
    [
      addToHistory,
      appendToAnswer,
      resetQueryStore,
      setCurrentAnswer,
      setGraphContext,
      setMetadata,
      setProcessingTime,
      setSources,
      setStreamStatus,
    ]
  );

  return { submit, reset, status: streamStatus };
}
