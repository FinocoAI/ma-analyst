interface Props {
  currentStep: string;
  progressPct: number;
}

export function LoadingSteps({ currentStep, progressPct }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-6">
      <div className="w-full max-w-md">
        <div className="flex justify-between text-sm text-gray-500 mb-2">
          <span>{currentStep}</span>
          <span>{progressPct.toFixed(0)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-stone-700 h-2 rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>
      <p className="text-sm text-gray-400">This may take a few minutes...</p>
    </div>
  );
}
