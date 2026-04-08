import { DimensionScore } from "@/lib/types";
import { DIMENSION_LABELS } from "@/lib/constants";

export function DimensionScoreBar({ dim }: { dim: DimensionScore }) {
  const pct = (dim.score / 10) * 100;
  const color = dim.score >= 7 ? "bg-green-500" : dim.score >= 4 ? "bg-yellow-400" : "bg-red-400";

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-600">
        <span>{DIMENSION_LABELS[dim.dimension] || dim.dimension}</span>
        <span className="font-medium">{dim.score.toFixed(1)} / 10</span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-gray-500">{dim.justification}</p>
    </div>
  );
}
