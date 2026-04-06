import { Signal } from "@/lib/types";
import { SIGNAL_STRENGTH_COLORS } from "@/lib/constants";

export function SignalCard({ signal }: { signal: Signal }) {
  return (
    <div className={`border rounded-lg p-3 text-sm ${SIGNAL_STRENGTH_COLORS[signal.strength]}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium uppercase tracking-wide opacity-70">
          {signal.source_quarter}
        </span>
        <span className="text-xs opacity-60">·</span>
        <span className="text-xs opacity-70">{signal.source_document}</span>
        <span className={`ml-auto text-xs font-medium capitalize`}>
          {signal.strength}
        </span>
      </div>
      <blockquote className="italic leading-relaxed mb-2">
        "{signal.quote}"
      </blockquote>
      <p className="text-xs opacity-70 not-italic">{signal.reasoning}</p>
    </div>
  );
}
