"use client";
import { useState, useEffect, useCallback } from "react";
import { PipelineStatus, PipelineStatusResponse, TargetProfile, ScoredProspect, ScoringWeights } from "@/lib/types";
import { getPipelineStatus, getPipelineRun, confirmProfile as apiConfirmProfile, rescorePipeline as apiRescorePipeline } from "@/lib/api";

interface PipelineState {
  runId: string | null;
  status: PipelineStatus | null;
  currentStep: string;
  progressPct: number;
  targetProfile: TargetProfile | null;
  scoredProspects: ScoredProspect[];
  error: string | null;
}

export function usePipeline() {
  const [state, setState] = useState<PipelineState>({
    runId: null,
    status: null,
    currentStep: "",
    progressPct: 0,
    targetProfile: null,
    scoredProspects: [],
    error: null,
  });

  const poll = useCallback(async (runId: string) => {
    try {
      const statusRes: PipelineStatusResponse = await getPipelineStatus(runId);
      setState((prev) => ({
        ...prev,
        status: statusRes.status,
        currentStep: statusRes.current_step,
        progressPct: statusRes.progress_pct,
        error: statusRes.error_message,
      }));

      if (statusRes.status === "profile_ready" || statusRes.status === "complete") {
        const full = await getPipelineRun(runId);
        setState((prev) => ({
          ...prev,
          targetProfile: full.target_profile || null,
          scoredProspects: full.scored_prospects || [],
        }));
      }
    } catch (e: any) {
      setState((prev) => ({ ...prev, error: e.message }));
    }
  }, []);

  useEffect(() => {
    if (!state.runId) return;
    if (state.status === "complete" || state.status === "failed") return;

    const interval = setInterval(() => poll(state.runId!), 2000);
    return () => clearInterval(interval);
  }, [state.runId, state.status, poll]);

  const startRun = (runId: string) => {
    setState({
      runId,
      status: "profiling",
      currentStep: "Analysing target company...",
      progressPct: 10,
      targetProfile: null,
      scoredProspects: [],
      error: null,
    });
  };

  const confirmProfile = async (profile: TargetProfile) => {
    if (!state.runId) return;
    await apiConfirmProfile(state.runId, profile);
    setState((prev) => ({ ...prev, status: "prospecting", progressPct: 35 }));
  };

  const triggerRescore = async (weights: ScoringWeights) => {
    if (!state.runId) return;
    setState((prev) => ({ ...prev, status: "scoring" }));
    try {
      await apiRescorePipeline(state.runId, weights);
    } catch (e: any) {
      setState((prev) => ({ ...prev, error: e.message }));
    }
  };

  const resumeRun = (runId: string) => {
    setState({
      runId,
      status: null,
      currentStep: "Resuming analysis...",
      progressPct: 0,
      targetProfile: null,
      scoredProspects: [],
      error: null,
    });
  };

  return { ...state, startRun, confirmProfile, triggerRescore, resumeRun };
}
