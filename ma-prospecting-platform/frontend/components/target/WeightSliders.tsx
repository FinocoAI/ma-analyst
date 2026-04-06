"use client";
import { ScoringWeights } from "@/lib/types";
import { DIMENSION_LABELS } from "@/lib/constants";

interface Props {
  weights: ScoringWeights;
  onUpdate: (key: keyof ScoringWeights, value: number) => void;
  isRescoring: boolean;
}

export function WeightSliders({ weights, onUpdate, isRescoring }: Props) {
  const total = Object.values(weights).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700">Matching Weights</h3>
        {isRescoring && <span className="text-xs text-stone-500 animate-pulse">Re-scoring...</span>}
        <span className={`text-xs ${Math.abs(total - 100) > 0.1 ? "text-red-500" : "text-gray-400"}`}>
          Total: {total.toFixed(0)}%
        </span>
      </div>

      {(Object.keys(weights) as (keyof ScoringWeights)[]).map((key) => (
        <div key={key}>
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>{DIMENSION_LABELS[key]}</span>
            <span>{weights[key]}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={50}
            step={5}
            value={weights[key]}
            onChange={(e) => onUpdate(key, Number(e.target.value))}
            className="w-full accent-stone-700"
          />
        </div>
      ))}
    </div>
  );
}
