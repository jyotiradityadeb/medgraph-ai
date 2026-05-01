import { motion } from "framer-motion";
import { BarChart2, Network, Search, Upload } from "lucide-react";

type AppPage = "query" | "graph" | "ingest" | "metrics";

interface SidebarProps {
  page: AppPage;
  onChangePage: (page: AppPage) => void;
}

const ITEMS: Array<{ key: AppPage; label: string; icon: typeof Search }> = [
  { key: "query", label: "Query", icon: Search },
  { key: "graph", label: "Graph", icon: Network },
  { key: "ingest", label: "Ingest", icon: Upload },
  { key: "metrics", label: "Metrics", icon: BarChart2 },
];

export function Sidebar({ page, onChangePage }: SidebarProps) {
  return (
    <motion.aside
      initial={{ width: 64 }}
      whileHover={{ width: 240 }}
      transition={{ type: "spring", damping: 24, stiffness: 240 }}
      className="group hidden h-screen shrink-0 border-r border-slate-200 bg-white md:block"
    >
      <div className="flex h-full flex-col gap-2 p-2">
        {ITEMS.map((item) => {
          const Icon = item.icon;
          const active = page === item.key;
          return (
            <button
              key={item.key}
              type="button"
              title={item.label}
              onClick={() => onChangePage(item.key)}
              className={`flex h-12 w-full items-center rounded-md px-3 transition ${
                active ? "bg-primary text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              <Icon className="h-5 w-5 shrink-0" />
              <span className="ml-3 overflow-hidden whitespace-nowrap text-sm font-medium opacity-0 transition-opacity group-hover:opacity-100">
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </motion.aside>
  );
}
