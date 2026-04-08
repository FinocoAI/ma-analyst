"use client";
import { useState, useEffect } from "react";

export interface RecentRun {
  runId: string;
  url: string;
  timestamp: number;
}

export function useRecentRuns() {
  const [runs, setRuns] = useState<RecentRun[]>([]);

  useEffect(() => {
    const loadRuns = () => {
      try {
        const stored = localStorage.getItem("recent_runs");
        if (stored) {
          setRuns(JSON.parse(stored));
        }
      } catch (e) {
        console.error("Failed to parse recent runs block", e);
      }
    };
    loadRuns();
    window.addEventListener("recent_runs_updated", loadRuns);
    return () => window.removeEventListener("recent_runs_updated", loadRuns);
  }, []);

  const addRun = (runId: string, url: string) => {
    const newRun: RecentRun = { runId, url, timestamp: Date.now() };
    const stored = localStorage.getItem("recent_runs");
    const prev = stored ? JSON.parse(stored) : [];
    const filtered = prev.filter((r: RecentRun) => r.runId !== runId);
    const updated = [newRun, ...filtered].slice(0, 10); // Keep last 10
    localStorage.setItem("recent_runs", JSON.stringify(updated));
    setRuns(updated);
    window.dispatchEvent(new Event("recent_runs_updated"));
  };

  return { runs, addRun };
}
