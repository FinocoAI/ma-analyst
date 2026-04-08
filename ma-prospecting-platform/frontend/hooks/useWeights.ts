"use client";
import { useState, useEffect, useRef } from "react";
import { ScoringWeights } from "@/lib/types";
import { DEFAULT_WEIGHTS } from "@/lib/constants";

export function useWeights(
  runId: string | null,
  isComplete: boolean,
  onDebouncedChange?: (weights: ScoringWeights) => void
) {
  const [weights, setWeights] = useState<ScoringWeights>(DEFAULT_WEIGHTS);
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);
  const prevWeightsStr = useRef<string>(JSON.stringify(DEFAULT_WEIGHTS));

  useEffect(() => {
    if (!runId || !isComplete) return;

    const currentWeightsStr = JSON.stringify(weights);
    if (currentWeightsStr === prevWeightsStr.current) return;
    
    const total = Object.values(weights).reduce((a, b) => a + b, 0);
    if (Math.abs(total - 100) > 0.1) return;
    
    if (debounceTimer.current) clearTimeout(debounceTimer.current);

    debounceTimer.current = setTimeout(() => {
      prevWeightsStr.current = currentWeightsStr;
      if (onDebouncedChange) {
        onDebouncedChange(weights);
      }
    }, 600);

    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [weights, runId, isComplete, onDebouncedChange]);

  const updateWeight = (key: keyof ScoringWeights, value: number) => {
    setWeights((prev) => ({ ...prev, [key]: value }));
  };

  return { weights, updateWeight };
}
