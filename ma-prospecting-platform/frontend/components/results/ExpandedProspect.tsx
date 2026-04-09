import { Signal, ScoredProspect } from "@/lib/types";
import { SignalCard } from "./SignalCard";
import { DimensionScoreBar } from "./DimensionScoreBar";
import { SOURCE_TYPE_LABELS, SOURCE_TYPE_COLORS } from "@/lib/constants";

// All 7 source types in preferred display order
const SOURCE_TYPE_ORDER = [
  "earnings_transcript",
  "annual_report",
  "sebi_filing",
  "investor_presentation",
  "board_resolution",
  "company_website",
  "press",
  "unknown",
] as const;

function groupBySourceType(signals: Signal[]): Record<string, Signal[]> {
  return signals.reduce((acc, s) => {
    const key = s.source_type || "unknown";
    (acc[key] = acc[key] || []).push(s);
    return acc;
  }, {} as Record<string, Signal[]>);
}

export function ExpandedProspect({ sp }: { sp: ScoredProspect }) {
  const grouped = groupBySourceType(sp.signals);
  const activeSourceTypes = SOURCE_TYPE_ORDER.filter((t) => (grouped[t] ?? []).length > 0);
  const totalSources = activeSourceTypes.length;

  return (
    <div className="grid grid-cols-2 gap-6 p-4 bg-gray-50 border-t border-gray-100">
      {/* Left column: signals + match reasoning */}
      <div className="space-y-4">
        <div>
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Acquisition Signals
            </h4>
            {sp.signals.length > 0 && (
              <span className="text-[10px] text-gray-400">
                {sp.signals.length} signal{sp.signals.length !== 1 ? "s" : ""} · {totalSources} source{totalSources !== 1 ? "s" : ""}
              </span>
            )}
          </div>

          {sp.signals.length === 0 ? (
            <p className="text-sm text-gray-400">No signals found.</p>
          ) : (
            <div className="space-y-5">
              {activeSourceTypes.map((sourceType) => (
                <div key={sourceType}>
                  {/* Source type group header */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${SOURCE_TYPE_COLORS[sourceType]}`}>
                      {SOURCE_TYPE_LABELS[sourceType]}
                    </span>
                    <span className="text-[10px] text-gray-400">
                      {grouped[sourceType].length} signal{grouped[sourceType].length !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {grouped[sourceType].map((signal) => (
                      <SignalCard key={signal.id} signal={signal} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {sp.match_reasoning && (
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Why This Match
            </h4>
            <div className="text-sm text-gray-700 space-y-1">
              {sp.match_reasoning.split("→").filter(Boolean).map((point, i) => (
                <p key={i} className="flex items-start gap-1">
                  <span className="text-stone-400 mt-0.5">→</span>
                  <span>{point.trim()}</span>
                </p>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right column: dimension scores + sources scanned */}
      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Dimension Scores
        </h4>
        <div className="space-y-3 mb-6">
          {sp.dimension_scores.map((dim) => (
            <DimensionScoreBar key={dim.dimension} dim={dim} />
          ))}
        </div>

        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Sources Searched
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {SOURCE_TYPE_ORDER.filter((t) => t !== "unknown").map((sourceType) => {
              const count = (grouped[sourceType] ?? []).length;
              const hasSignals = count > 0;
              return (
                <span
                  key={sourceType}
                  className={`text-[9px] px-2 py-0.5 rounded border font-medium transition-colors ${
                    hasSignals
                      ? SOURCE_TYPE_COLORS[sourceType]
                      : "bg-gray-100 border-gray-200 text-gray-400"
                  }`}
                >
                  {hasSignals && "✓ "}{SOURCE_TYPE_LABELS[sourceType]}
                  {hasSignals && ` (${count})`}
                </span>
              );
            })}
          </div>
          <p className="text-[10px] text-gray-400 mt-2 italic">
            All 7 source types searched per prospect via live web search.
          </p>
        </div>
      </div>
    </div>
  );
}
