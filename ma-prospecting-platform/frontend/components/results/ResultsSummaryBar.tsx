import { ScoredProspect, Signal } from "@/lib/types";

interface Props {
  scoredProspects: ScoredProspect[];
}

export function ResultsSummaryBar({ scoredProspects }: Props) {
  const totalSignals = scoredProspects.flatMap((sp) => sp.signals);
  const strongSignals = totalSignals.filter((s) => s.strength === "high").length;
  const avgScore = scoredProspects.length
    ? scoredProspects.reduce((sum, sp) => sum + sp.weighted_total, 0) / scoredProspects.length
    : 0;
  const sourcesScanned = new Set(totalSignals.map((s) => s.source_document)).size;

  const stats = [
    { label: "Total Matches", value: scoredProspects.length },
    { label: "Strong Signals", value: strongSignals },
    { label: "Avg Match Score", value: avgScore.toFixed(0) },
    { label: "Sources Scanned", value: sourcesScanned.toLocaleString() },
  ];

  return (
    <div className="grid grid-cols-4 gap-4 mb-4">
      {stats.map((stat) => (
        <div key={stat.label} className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
          <p className="text-xs text-gray-500 mt-0.5">{stat.label}</p>
        </div>
      ))}
    </div>
  );
}
