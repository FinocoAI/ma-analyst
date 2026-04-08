"use client";
import { useState } from "react";
import { UserFilters, BuyerPersona } from "@/lib/types";
import { createPipelineRun } from "@/lib/api";
import { DEFAULT_FILTERS, DEFAULT_WEIGHTS, PERSONA_LABELS } from "@/lib/constants";
import { useRecentRuns } from "@/hooks/useRecentRuns";

interface Props {
  onRunStarted: (runId: string) => void;
}

const PERSONA_OPTIONS: Array<{ value: BuyerPersona; disabled?: false } | { value: "private"; disabled: true }> = [
  { value: "strategic" },
  { value: "private_equity" },
  { value: "conglomerate" },
  { value: "private", disabled: true },
];

export function TargetInputForm({ onRunStarted }: Props) {
  const [url, setUrl] = useState("");
  const [filters, setFilters] = useState<UserFilters>(DEFAULT_FILTERS);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { addRun } = useRecentRuns();

  const togglePersona = (persona: BuyerPersona) => {
    setFilters((prev) => ({
      ...prev,
      personas: prev.personas.includes(persona)
        ? prev.personas.filter((p) => p !== persona)
        : [...prev.personas, persona],
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await createPipelineRun(url.trim(), filters, DEFAULT_WEIGHTS);
      addRun(result.run_id, url.trim());
      onRunStarted(result.run_id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Target Company URL
        </label>
        <div className="flex gap-3">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.elex.ch/en/"
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-stone-500"
          />
          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className="px-5 py-2.5 bg-stone-800 text-white text-sm font-medium rounded-lg hover:bg-stone-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "Analysing..." : "Analyse"}
          </button>
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Buyer Persona</label>
        <div className="flex gap-3">
          {PERSONA_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => {
                if (!option.disabled) {
                  togglePersona(option.value);
                }
              }}
              disabled={option.disabled}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                option.disabled
                  ? "bg-stone-100 text-stone-400 border-stone-200 cursor-not-allowed"
                  : filters.personas.includes(option.value)
                  ? "bg-stone-800 text-white border-stone-800"
                  : "bg-white text-gray-600 border-gray-300 hover:border-gray-400"
              }`}
            >
              {option.disabled ? "Private (Coming soon)" : PERSONA_LABELS[option.value]}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Revenue Min (USD M)
          </label>
          <input
            type="number"
            value={filters.revenue_min_usd_m ?? ""}
            onChange={(e) => setFilters((prev) => ({ ...prev, revenue_min_usd_m: e.target.value ? Number(e.target.value) : null }))}
            placeholder="e.g. 50"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-stone-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Revenue Max (USD M)
          </label>
          <input
            type="number"
            value={filters.revenue_max_usd_m ?? ""}
            onChange={(e) => setFilters((prev) => ({ ...prev, revenue_max_usd_m: e.target.value ? Number(e.target.value) : null }))}
            placeholder="e.g. 5000"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-stone-500"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Results to show
        </label>
        <select
          value={filters.num_results}
          onChange={(e) => setFilters((prev) => ({ ...prev, num_results: Number(e.target.value) }))}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-stone-500"
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
        </select>
      </div>
    </form>
  );
}
