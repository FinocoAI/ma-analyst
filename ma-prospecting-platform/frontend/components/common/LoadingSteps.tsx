interface Props {
  currentStep: string;
  progressPct: number;
}

export function LoadingSteps({ currentStep, progressPct }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4 min-h-[400px]">
      <div className="w-full max-w-lg bg-white rounded-2xl border border-stone-200 shadow-sm p-8 space-y-8 animate-in fade-in zoom-in duration-500">
        <div className="flex flex-col items-center text-center space-y-3">
          {/* Animated Spinner Core */}
          <div className="relative w-16 h-16">
            <div className="absolute inset-0 rounded-full border-4 border-stone-100" />
            <div 
              className="absolute inset-0 rounded-full border-4 border-stone-700 border-t-transparent animate-spin" 
              style={{ animationDuration: '0.8s' }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs font-bold text-stone-600 tracking-tighter">M&A</span>
            </div>
          </div>
          
          <div className="space-y-1">
            <h3 className="text-lg font-semibold text-stone-900 tracking-tight">
              Executing Prospecting Pipeline
            </h3>
            <p className="text-sm text-stone-500 max-w-sm">
              Our agents are currently scanning global transcripts and filings for inorganic growth signals.
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex justify-between items-end">
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest leading-none mb-1">
                Current Operation
              </span>
              <span className="text-sm font-medium text-stone-700 animate-pulse">
                {currentStep}
              </span>
            </div>
            <span className="text-2xl font-bold font-mono text-stone-900 tabular-nums">
              {progressPct.toFixed(0)}%
            </span>
          </div>

          <div className="relative">
            <div className="w-full bg-stone-100 rounded-full h-3 overflow-hidden">
              <div
                className="bg-stone-800 h-full rounded-full transition-all duration-1000 ease-out shadow-[0_0_8px_rgba(43,43,43,0.3)]"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            {/* Glossy overlay */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent pointer-events-none" />
          </div>
        </div>

        <div className="pt-4 border-t border-stone-100 flex justify-center text-center">
          <p className="text-xs text-stone-400 leading-relaxed italic max-w-sm">
            Our intelligence engine is currently cross-referencing global financial disclosures and management commentary to ensure precise alignment with your mandate. High-fidelity signal extraction in progress.
          </p>
        </div>
      </div>
    </div>
  );
}
