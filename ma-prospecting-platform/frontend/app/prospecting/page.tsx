"use client";

import { usePipeline } from "@/hooks/usePipeline";
import { useWeights } from "@/hooks/useWeights";
import { TargetInputForm } from "@/components/target/TargetInputForm";
import { TargetProfileCard } from "@/components/target/TargetProfileCard";
import { WeightSliders } from "@/components/target/WeightSliders";
import { LoadingSteps } from "@/components/common/LoadingSteps";
import { ResultsSummaryBar } from "@/components/results/ResultsSummaryBar";
import { ResultsTable } from "@/components/results/ResultsTable";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState, useCallback } from "react";

const CHAT_WIDTH_STORAGE_KEY = "ma-chat-panel-width";

function clampChatWidth(w: number): number {
  if (typeof window === "undefined") {
    return Math.min(560, Math.max(260, w));
  }
  const max = Math.min(560, Math.floor(window.innerWidth * 0.45));
  return Math.min(max, Math.max(260, w));
}

export default function ProspectingPage() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-gray-500">Loading...</div>}>
      <ProspectingContent />
    </Suspense>
  );
}

function ProspectingContent() {
  const pipeline = usePipeline();
  const searchParams = useSearchParams();
  const [chatWidth, setChatWidth] = useState(320);
  const dragRef = useRef<{ startX: number; startW: number } | null>(null);
  const latestChatWidth = useRef(320);

  useEffect(() => {
    latestChatWidth.current = chatWidth;
  }, [chatWidth]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(CHAT_WIDTH_STORAGE_KEY);
      if (raw) {
        const n = parseInt(raw, 10);
        if (!Number.isNaN(n)) {
          const clamped = clampChatWidth(n);
          setChatWidth(clamped);
          latestChatWidth.current = clamped;
        }
      }
    } catch {
      /* ignore */
    }
  }, []);

  const onResizeMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragRef.current = { startX: e.clientX, startW: latestChatWidth.current };
      document.body.style.cursor = "col-resize";
      const onMove = (ev: MouseEvent) => {
        if (!dragRef.current) return;
        const { startX, startW } = dragRef.current;
        const next = clampChatWidth(startW + startX - ev.clientX);
        latestChatWidth.current = next;
        setChatWidth(next);
      };
      const onUp = () => {
        dragRef.current = null;
        document.body.style.cursor = "";
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
        try {
          localStorage.setItem(CHAT_WIDTH_STORAGE_KEY, String(latestChatWidth.current));
        } catch {
          /* ignore */
        }
      };
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    },
    []
  );

  useEffect(() => {
    const runId = searchParams.get("runId");
    if (runId && pipeline.runId !== runId) {
      pipeline.resumeRun(runId);
    }
  }, [searchParams]);

  
  // We keep the results on screen if we already had them at least once
  const hasResults = pipeline.scoredProspects.length > 0;
  
  const { weights, updateWeight } = useWeights(
    pipeline.runId,
    pipeline.status === "complete",
    pipeline.triggerRescore
  );

  // If we have results, don't revert back to the main LoadingSteps view
  const isRunning = pipeline.status && 
    !["complete", "failed", "profile_ready"].includes(pipeline.status) && 
    !hasResults;
    
  const showResults = pipeline.status === "complete" || hasResults;
  const isProfileReady = pipeline.status === "profile_ready";
  const isRescoring = pipeline.status === "scoring";

  return (
    <div className="flex h-screen min-h-0">
      {/* Center panel */}
      <div className="flex-1 flex flex-col overflow-y-auto min-h-0 bg-white text-gray-900">
        <div className="p-6 border-b border-gray-200 bg-white">
          <h2 className="text-base font-semibold text-gray-800 mb-1">Sell-side Prospecting</h2>
          <p className="text-sm text-gray-500">Find ideal buyers for your target company</p>
        </div>

        <div className="p-6 space-y-6 flex-1">
          {/* Input form — shown when no run is active */}
          {!pipeline.runId && (
            <TargetInputForm onRunStarted={pipeline.startRun} />
          )}

          {/* Profile confirmation — shown after Step 1 completes */}
          {isProfileReady && pipeline.targetProfile && (
            <TargetProfileCard
              profile={pipeline.targetProfile}
              onConfirm={pipeline.confirmProfile}
            />
          )}

          {/* Loading progress — shown during initial pipeline run */}
          {isRunning && (
            <LoadingSteps
              currentStep={pipeline.currentStep}
              progressPct={pipeline.progressPct}
            />
          )}

          {/* Error state */}
          {pipeline.status === "failed" && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm font-medium text-red-800">Pipeline failed</p>
              <p className="text-sm text-red-600 mt-1">{pipeline.error}</p>
              <button
                onClick={() => window.location.href = '/prospecting'}
                className="mt-3 text-sm text-red-700 underline"
              >
                Start over
              </button>
            </div>
          )}

          {/* Results — shown when complete or rescoring */}
          {showResults && pipeline.scoredProspects.length > 0 && (
            <>
              <div className="flex items-center justify-between">
                <ResultsSummaryBar scoredProspects={pipeline.scoredProspects} />
                <button
                  onClick={() => window.location.href = '/prospecting'}
                  className="px-4 py-2 bg-white text-sm font-medium text-stone-700 border border-stone-300 rounded-lg hover:bg-stone-50 transition-colors"
                >
                  Start New Analysis
                </button>
              </div>

              <WeightSliders
                weights={weights}
                onUpdate={updateWeight}
                isRescoring={isRescoring}
              />

              <ResultsTable prospects={pipeline.scoredProspects} />
            </>
          )}
        </div>
      </div>

      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize chat panel"
        onMouseDown={onResizeMouseDown}
        className="w-1 shrink-0 cursor-col-resize select-none bg-stone-100 hover:bg-stone-200 border-l border-r border-stone-200"
      />

      {/* Right panel — Chat */}
      <div
        className="border-l border-gray-200 bg-white text-gray-900 flex flex-col shrink-0 min-h-0 overflow-hidden"
        style={{ width: chatWidth }}
      >
        <ChatPanel runId={pipeline.runId} isReady={showResults} />
      </div>
    </div>
  );
}
