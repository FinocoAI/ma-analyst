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
        <div className="space-y-3">
          {sp.dimension_scores.map((dim) => (
            <DimensionScoreBar key={dim.dimension} dim={dim} />
          ))}
        </div>
      </div>
    </div>
  );
}
