import { useEffect, useState } from "react";
import { Brain } from "lucide-react";
import toast from "react-hot-toast";

import { api } from "@/api/client";
import type { HealthStatus } from "@/types";

export function TopBar() {
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    let mounted = true;

    const check = async () => {
      try {
        const result = await api.health();
        if (mounted) setHealth(result);
      } catch (error) {
        if (mounted) {
          setHealth({ status: "error", services: { qdrant: false, neo4j: false } });
          toast.error(error instanceof Error ? error.message : "Health check failed");
        }
      }
    };

    void check();
    const timer = window.setInterval(() => void check(), 30_000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  const healthy = Boolean(health?.services.neo4j && health?.services.qdrant);

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-slate-200 bg-white px-4">
      <div className="flex items-center gap-2">
        <Brain className="h-5 w-5 text-primary" />
        <h1 className="text-base font-semibold text-slate-800">MedGraph AI</h1>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${healthy ? "bg-emerald-500" : "bg-red-500"}`} />
          <span className="text-xs text-slate-500">{healthy ? "Services healthy" : "Degraded"}</span>
        </div>
        <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-600">
          gpt-4o
        </span>
      </div>
    </header>
  );
}
