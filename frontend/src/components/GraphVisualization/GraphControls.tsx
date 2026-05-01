import { Maximize2, Minus, Plus, RotateCcw } from "lucide-react";

interface GraphControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  onFullscreen: () => void;
}

export function GraphControls({ onZoomIn, onZoomOut, onReset, onFullscreen }: GraphControlsProps) {
  const btnClass = "rounded-md border border-slate-300 bg-white p-2 text-slate-600 hover:bg-slate-50";
  return (
    <div className="absolute right-3 top-3 z-10 flex gap-2">
      <button type="button" title="Zoom in" className={btnClass} onClick={onZoomIn}>
        <Plus className="h-4 w-4" />
      </button>
      <button type="button" title="Zoom out" className={btnClass} onClick={onZoomOut}>
        <Minus className="h-4 w-4" />
      </button>
      <button type="button" title="Reset camera" className={btnClass} onClick={onReset}>
        <RotateCcw className="h-4 w-4" />
      </button>
      <button type="button" title="Fullscreen" className={btnClass} onClick={onFullscreen}>
        <Maximize2 className="h-4 w-4" />
      </button>
    </div>
  );
}
