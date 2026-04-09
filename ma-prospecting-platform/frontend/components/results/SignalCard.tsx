import { Signal } from "@/lib/types";
import { SIGNAL_STRENGTH_COLORS } from "@/lib/constants";

export function SignalCard({ signal }: { signal: Signal }) {
  return (
    <div className={`border rounded-xl p-4 transition-all hover:shadow-sm ${SIGNAL_STRENGTH_COLORS[signal.strength]}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] font-bold uppercase tracking-wider opacity-60">
          {signal.source_quarter}
        </span>
        <span className="text-gray-300">|</span>
        {signal.source_url ? (
          <a
            href={signal.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-medium hover:underline flex items-center gap-1 group"
          >
            <span>{signal.source_document}</span>
            <svg className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        ) : (
          <span className="text-xs font-medium">{signal.source_document}</span>
        )}
        <span className={`ml-auto text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded-md border border-current opacity-80`}>
          {signal.strength}
        </span>
      </div>
      
      <div className="relative mb-3">
        <span className="absolute -left-2 -top-1 text-2xl text-current opacity-20 pointer-events-none">"</span>
        <p className="text-sm font-medium leading-relaxed italic pr-2">
          {signal.quote}
        </p>
      </div>
      
      <div className="flex items-start gap-2 pt-3 border-t border-black/5">
        <span className="text-xs mt-0.5 opacity-50">→</span>
        <p className="text-xs leading-relaxed opacity-80">{signal.reasoning}</p>
      </div>
    </div>
  );
}
