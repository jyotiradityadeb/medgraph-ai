import { Activity, AlertTriangle, Clock3, Database } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import toast from "react-hot-toast";

import { api } from "@/api/client";
import type { MetricsSummary } from "@/types";

function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

function sumErrors(errorCounts: Record<string, number>): number {
  return Object.values(errorCounts).reduce((sum, value) => sum + value, 0);
}

export function MetricsPage() {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<number | null>(null);
  const [ageSeconds, setAgeSeconds] = useState(0);

  useEffect(() => {
    let mounted = true;

    const loadMetrics = async () => {
      try {
        const data = await api.metrics();
        if (!mounted) return;
        setMetrics(data);
        setLastUpdatedAt(Date.now());
        setAgeSeconds(0);
      } catch (error) {
        if (!mounted) return;
        toast.error(error instanceof Error ? error.message : "Failed to load metrics");
      } finally {
        if (mounted) setLoading(false);
      }
    };

    void loadMetrics();
    const refreshTimer = window.setInterval(() => void loadMetrics(), 10_000);
    const ageTimer = window.setInterval(() => setAgeSeconds((value) => value + 1), 1_000);

    return () => {
      mounted = false;
      window.clearInterval(refreshTimer);
      window.clearInterval(ageTimer);
    };
  }, []);

  const modalityChart = useMemo(() => {
    const usage = metrics?.modality_usage ?? {};
    return [
      { name: "Text", value: usage.text ?? 0 },
      { name: "Image", value: usage.image ?? 0 },
      { name: "Audio", value: usage.audio ?? 0 },
      { name: "Table", value: usage.table ?? 0 },
    ];
  }, [metrics]);

  const errorEntries = useMemo(
    () => Object.entries(metrics?.error_counts ?? {}).sort((a, b) => b[1] - a[1]),
    [metrics]
  );

  if (loading && !metrics) {
    return <section className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">Loading metrics...</section>;
  }

  if (!metrics) {
    return (
      <section className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Metrics are unavailable right now.
      </section>
    );
  }

  const cacheHitPercent = Math.round((metrics.cache.hit_rate ?? 0) * 100);
  const totalErrors = sumErrors(metrics.error_counts);

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4">
        <div>
          <h2 className="text-base font-semibold text-slate-800">System Metrics</h2>
          <p className="text-xs text-slate-500">Uptime: {formatUptime(metrics.uptime_seconds)}</p>
        </div>
        <p className="text-xs text-slate-500">
          Last updated {ageSeconds}s ago
          {lastUpdatedAt ? ` · ${new Date(lastUpdatedAt).toLocaleTimeString()}` : ""}
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-2 inline-flex rounded-md bg-blue-50 p-2 text-primary">
            <Activity className="h-4 w-4" />
          </div>
          <p className="text-xs text-slate-500">Total Queries</p>
          <p className="text-xl font-semibold text-slate-800">{metrics.total_queries}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-2 inline-flex rounded-md bg-emerald-50 p-2 text-accent">
            <Clock3 className="h-4 w-4" />
          </div>
          <p className="text-xs text-slate-500">Avg Latency (ms)</p>
          <p className="text-xl font-semibold text-slate-800">{metrics.avg_latency_ms}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-2 inline-flex rounded-md bg-indigo-50 p-2 text-indigo-600">
            <Database className="h-4 w-4" />
          </div>
          <p className="text-xs text-slate-500">Cache Hit Rate (%)</p>
          <p className="text-xl font-semibold text-slate-800">{cacheHitPercent}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-2 inline-flex rounded-md bg-amber-50 p-2 text-warning">
            <AlertTriangle className="h-4 w-4" />
          </div>
          <p className="text-xs text-slate-500">Error Count</p>
          <p className="text-xl font-semibold text-slate-800">{totalErrors}</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Modality Usage</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modalityChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="name" stroke="#64748B" />
                <YAxis allowDecimals={false} stroke="#64748B" />
                <Tooltip />
                <Bar dataKey="value" fill="#0F4C81" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Recent Errors</h3>
          {errorEntries.length === 0 ? (
            <p className="text-sm text-slate-500">No recent errors recorded.</p>
          ) : (
            <ul className="space-y-2">
              {errorEntries.map(([key, value]) => (
                <li key={key} className="flex items-center justify-between rounded border border-slate-200 px-2 py-1.5 text-sm">
                  <span className="truncate text-slate-700">{key}</span>
                  <span className="ml-3 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{value}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}

