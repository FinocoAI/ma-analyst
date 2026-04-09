import { ScoredProspect } from "@/lib/types";
import { SignalCard } from "./SignalCard";
import { DimensionScoreBar } from "./DimensionScoreBar";

export function ExpandedProspect({ sp }: { sp: ScoredProspect }) {
  return (
    <div className="grid grid-cols-2 gap-6 p-4 bg-gray-50 border-t border-gray-100">
      <div className="space-y-4">
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Acquisition Signals
          </h4>
          {sp.signals.length === 0 ? (
            <p className="text-sm text-gray-400">No signals found.</p>
          ) : (
            <div className="space-y-2">
              {sp.signals.map((signal) => (
                <SignalCard key={signal.id} signal={signal} />
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
            Data Sources Scanned
          </h4>
          <div className="flex flex-wrap gap-2">
            {[
              "Earnings call",
              "Annual reports",
              "SEBI Filings",
              "News & Press",
              "Investor presentations",
            ].map((src) => {
              const hasSignal = sp.signals.some((s) => 
                s.source_document?.toLowerCase().includes(src.toLowerCase().split(' ')[0])
              );
              return (
                <span
                  key={src}
                  className={`text-[10px] px-2 py-0.5 rounded border transition-colors ${
                    hasSignal
                      ? "bg-green-50 border-green-200 text-green-700 font-medium"
                      : "bg-gray-100 border-gray-200 text-gray-400"
                  }`}
                >
                  {hasSignal && "✓ "}{src}
                </span>
              );
            })}
          </div>
          <p className="text-[10px] text-gray-400 mt-2 italic">
            Agent dynamically prioritizes sources based on buyer country and listing status.
          </p>
        </div>
      </div>
    </div>
  );
}
