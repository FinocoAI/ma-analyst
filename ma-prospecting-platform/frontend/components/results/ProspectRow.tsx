"use client";
import { useState } from "react";
import { ScoredProspect } from "@/lib/types";
import { PersonaBadge } from "@/components/common/PersonaBadge";
import { ScoreBadge } from "@/components/common/ScoreBadge";
import { ExpandedProspect } from "./ExpandedProspect";
import { SIGNAL_STRENGTH_COLORS } from "@/lib/constants";

export function ProspectRow({ sp }: { sp: ScoredProspect }) {
  const [expanded, setExpanded] = useState(false);
  const p = sp.prospect;

  return (
    <>
      <tr
        className="hover:bg-gray-50 cursor-pointer border-b border-gray-100"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="px-4 py-3 text-sm text-gray-500 w-10">{sp.rank}</td>
        <td className="px-4 py-3">
          <div className="font-medium text-gray-900 text-sm">{p.company_name}</div>
          {p.ticker && <div className="text-xs text-gray-400">{p.ticker}</div>}
        </td>
        <td className="px-4 py-3">
          <PersonaBadge persona={p.persona} />
        </td>
        <td className="px-4 py-3 text-sm text-gray-600 max-w-[160px] truncate">{p.sector}</td>
        <td className="px-4 py-3 text-sm text-gray-600">
          {p.estimated_revenue_inr_cr
            ? `₹${p.estimated_revenue_inr_cr.toLocaleString()} Cr`
            : p.estimated_revenue_usd_m
            ? `$${p.estimated_revenue_usd_m}M`
            : "—"}
        </td>
        <td className="px-4 py-3">
          <ScoreBadge score={sp.weighted_total} />
        </td>
        <td className="px-4 py-3 text-sm text-gray-600 max-w-[200px]">
          {sp.top_signal ? (
            <span className={`inline-block text-xs px-1.5 py-0.5 rounded border ${SIGNAL_STRENGTH_COLORS[sp.top_signal.strength]} truncate max-w-full`}>
              {sp.top_signal.quote.substring(0, 60)}...
            </span>
          ) : "—"}
        </td>
        <td className="px-4 py-3 text-xs text-gray-400">
          {sp.top_signal?.source_quarter || "—"}
        </td>
        <td className="px-4 py-3 text-gray-400">
          <span className="text-xs">{expanded ? "▲" : "▼"}</span>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={9} className="p-0">
            <ExpandedProspect sp={sp} />
          </td>
        </tr>
      )}
    </>
  );
}
