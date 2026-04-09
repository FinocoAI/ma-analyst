import { Signal } from "@/lib/types";
import { SIGNAL_STRENGTH_COLORS } from "@/lib/constants";

export function SignalCard({ signal }: { signal: Signal }) {
  const signalTypeLabel = signal.signal_type.replace(/_/g, " ").toUpperCase();

  return (
    <div className={`group border rounded-xl overflow-hidden transition-all hover:shadow-md ${SIGNAL_STRENGTH_COLORS[signal.strength]} flex flex-col`}>
      {/* Header: Metadata & Source Link */}
      <div className="px-4 py-2 border-b border-black/5 bg-white/40 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-current opacity-60" />
          <span className="text-[10px] font-bold tracking-widest uppercase opacity-70">
            {signalTypeLabel}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono opacity-50">{signal.source_quarter}</span>
          <span className="text-gray-300">|</span>
          {signal.source_url ? (
            <a
              href={signal.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] font-bold underline hover:no-underline flex items-center gap-0.5"
            >
              {signal.source_document}
              <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          ) : (
            <span className="text-[10px] font-bold">{signal.source_document}</span>
          )}
        </div>
      </div>

      {/* Body: The Verbatim Quote */}
      <div className="p-4 space-y-4">
        <div className="relative">
          <div className="absolute -left-1 top-0 bottom-0 w-1 bg-current opacity-20 rounded-full" />
          <div className="pl-4">
            <h4 className="text-[9px] font-bold uppercase tracking-tighter opacity-40 mb-1">Verbatim Transcript Quote</h4>
            <p className="text-sm font-semibold leading-relaxed font-mono tracking-tight bg-white/20 p-2 rounded border border-black/5">
              "{signal.quote}"
            </p>
          </div>
        </div>

        {/* Dynamic Context (The lines around it) */}
        {signal.source_context && (
          <div className="pl-4">
            <h4 className="text-[9px] font-bold uppercase tracking-tighter opacity-40 mb-1">Document Context</h4>
            <p className="text-xs leading-relaxed opacity-60 italic">
              ...{signal.source_context}...
            </p>
          </div>
        )}

        {/* Analyst Interpretation */}
        <div className="pt-3 border-t border-black/5 flex gap-3">
          <div className="bg-white/60 px-1.5 py-0.5 rounded text-[9px] font-black uppercase h-fit mt-0.5 shadow-sm border border-black/5">
            AIS
          </div>
          <p className="text-xs leading-relaxed font-medium">
            {signal.reasoning}
          </p>
        </div>
      </div>
      
      {/* Footer: Strength tagging */}
      <div className="mt-auto px-4 py-1.5 bg-black/5 flex justify-end">
        <span className="text-[9px] font-black tracking-[0.2em] uppercase opacity-40">
          Signal Strength: {signal.strength}
        </span>
      </div>
    </div>
  );
}
