import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Toaster } from "react-hot-toast";

import { Sidebar } from "@/components/Layout/Sidebar";
import { TopBar } from "@/components/Layout/TopBar";
import { GraphExplorerPage } from "@/pages/GraphExplorerPage";
import { IngestPage } from "@/pages/IngestPage";
import { MetricsPage } from "@/pages/MetricsPage";
import { QueryPage } from "@/pages/QueryPage";

type AppPage = "query" | "graph" | "ingest" | "metrics";

const queryClient = new QueryClient();

export default function App() {
  const [page, setPage] = useState<AppPage>("query");

  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex min-h-screen bg-medical-bg text-slate-800">
        <Sidebar page={page} onChangePage={setPage} />
        <div className="flex min-h-screen flex-1 flex-col">
          <TopBar />
          <main className="flex-1 p-4 md:p-6">
            {page === "query" && <QueryPage />}
            {page === "graph" && <GraphExplorerPage />}
            {page === "ingest" && <IngestPage />}
            {page === "metrics" && <MetricsPage />}
          </main>
        </div>
      </div>
      <Toaster position="top-right" />
    </QueryClientProvider>
  );
}
