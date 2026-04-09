"use client";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useRecentRuns } from "@/hooks/useRecentRuns";

interface Props {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: Props) {
  return (
    <Suspense fallback={<aside className={`bg-stone-900 ${collapsed ? "w-16" : "w-56"}`} />}>
      <SidebarContent collapsed={collapsed} onToggle={onToggle} />
    </Suspense>
  );
}

function SidebarContent({ collapsed, onToggle }: Props) {
  const { runs } = useRecentRuns();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const activeRunId = searchParams?.get("runId");
  const onProspecting = pathname?.startsWith("/prospecting") ?? false;

  return (
    <aside
      className={`min-h-screen bg-stone-900 text-white flex flex-col py-6 shrink-0 transition-[width] duration-200 ease-out overflow-hidden ${
        collapsed ? "w-16 px-2 items-center" : "w-56 px-4"
      }`}
    >
      <div className={`flex w-full mb-2 ${collapsed ? "justify-center" : "justify-end"}`}>
        <button
          type="button"
          onClick={onToggle}
          className="rounded-md p-1.5 text-stone-400 hover:text-white hover:bg-stone-800"
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <span aria-hidden className="text-lg leading-none tabular-nums">
            {collapsed ? "\u00bb" : "\u00ab"}
          </span>
        </button>
      </div>

      {!collapsed && (
        <>
          <div className="mb-8">
            <h1 className="text-lg font-semibold tracking-tight">M&A Prospecting</h1>
            <p className="text-xs text-stone-400 mt-1">Sell-side intelligence</p>
          </div>

          <nav className="flex flex-col gap-1">
            <Link
              href="/prospecting"
              className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium text-left transition-colors ${
                onProspecting && !activeRunId
                  ? "bg-stone-700 text-white"
                  : "text-stone-400 hover:text-white hover:bg-stone-800"
              }`}
            >
              <span className={`w-2 h-2 rounded-full shrink-0 ${onProspecting ? "bg-green-400" : "bg-stone-600"}`} />
              Prospecting
            </Link>

            <button
              type="button"
              disabled
              className="flex items-center gap-2 px-3 py-2 rounded-md text-stone-500 text-sm font-medium text-left cursor-not-allowed"
            >
              <span className="w-2 h-2 rounded-full bg-stone-600 shrink-0" />
              Buy-side
              <span className="ml-auto text-xs bg-stone-700 text-stone-400 px-1.5 py-0.5 rounded">
                Soon
              </span>
            </button>
          </nav>

          <div className="mt-8 w-full">
            <h3 className="px-3 text-xs font-semibold text-stone-500 uppercase tracking-wider mb-2">
              Recent Runs
            </h3>
            <nav className="flex flex-col gap-1">
              {runs.map((r) => (
                <Link
                  key={r.runId}
                  href={`/prospecting?runId=${r.runId}`}
                  className={`px-3 py-2 text-xs rounded-md truncate block transition-colors ${
                    activeRunId === r.runId
                      ? "bg-stone-800 text-white font-medium"
                      : "text-stone-300 hover:text-white hover:bg-stone-800"
                  }`}
                  title={r.url}
                >
                  {r.url.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                </Link>
              ))}
              {runs.length === 0 && (
                <span className="px-3 text-xs text-stone-600">No recent runs</span>
              )}
            </nav>
          </div>
        </>
      )}

      {collapsed && (
        <nav className="flex flex-col gap-4 items-center w-full mt-4" aria-label="Primary">
          <Link
            href="/prospecting"
            className="flex items-center justify-center w-9 h-9 rounded-md bg-stone-700 hover:bg-stone-600"
            title="Prospecting"
            aria-current={onProspecting ? "page" : undefined}
          >
            <span className="w-2 h-2 rounded-full bg-green-400" />
          </Link>
          <span
            role="button"
            aria-disabled="true"
            aria-label="Buy-side (coming soon)"
            className="flex items-center justify-center w-9 h-9 rounded-md text-stone-600 cursor-not-allowed opacity-60"
            title="Buy-side (soon)"
          >
            <span className="w-2 h-2 rounded-full bg-stone-600" />
          </span>
        </nav>
      )}
    </aside>
  );
}
