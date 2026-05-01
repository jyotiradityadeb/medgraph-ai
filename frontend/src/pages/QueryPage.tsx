import { QueryPanel } from "@/components/QueryPanel";
import { ResultsPanel } from "@/components/ResultsPanel";

export function QueryPage() {
  return (
    <div className="grid gap-4 lg:grid-cols-[40%_60%]">
      <QueryPanel />
      <ResultsPanel />
    </div>
  );
}
