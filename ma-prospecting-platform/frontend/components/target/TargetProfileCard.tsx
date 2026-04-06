"use client";
import { useState } from "react";
import { TargetProfile, ScrapeContentQuality } from "@/lib/types";

function qualityBadge(q: ScrapeContentQuality | undefined) {
  switch (q) {
    case "curl_boost":
      return { label: "Profile ready (TLS fetch)", className: "bg-sky-50 text-sky-800 border border-sky-200" };
    case "exa_enriched":
      return { label: "Profile ready (Exa text)", className: "bg-violet-50 text-violet-800 border border-violet-200" };
    case "playwright":
      return { label: "Profile ready (browser render)", className: "bg-emerald-50 text-emerald-800 border border-emerald-200" };
    case "low":
      return {
        label: "Limited source text — review fields",
        className: "bg-amber-50 text-amber-900 border border-amber-300",
      };
    default:
      return { label: "Profile ready", className: "bg-stone-100 text-stone-600" };
  }
}

interface Props {
  profile: TargetProfile;
  onConfirm: (profile: TargetProfile) => void;
}

export function TargetProfileCard({ profile, onConfirm }: Props) {
  const [edited, setEdited] = useState<TargetProfile>(profile);

  const update = (key: keyof TargetProfile, value: any) => {
    setEdited((prev) => ({ ...prev, [key]: value }));
  };

  const badge = qualityBadge(edited.scrape_content_quality);

  return (
    <div className="border border-gray-200 rounded-xl p-5 bg-white space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{edited.company_name}</h2>
          <p className="text-sm text-gray-500">{edited.url}</p>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full shrink-0 ${badge.className}`}>{badge.label}</span>
      </div>

      <p className="text-sm text-gray-600">{edited.description}</p>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">Sector Classification</label>
        <div className="flex items-center gap-2 flex-wrap">
          {["sector_l1", "sector_l2", "sector_l3"].map((key, i) => (
            <div key={key} className="flex items-center gap-2">
              {i > 0 && <span className="text-gray-400">›</span>}
              <input
                value={(edited as any)[key]}
                onChange={(e) => update(key as keyof TargetProfile, e.target.value)}
                className="border-b border-gray-300 text-sm text-gray-800 bg-transparent focus:outline-none focus:border-stone-600 px-1"
              />
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-xs text-gray-500">Technologies</span>
          <p className="text-gray-800">{(edited.key_technologies || []).join(", ") || "—"}</p>
        </div>
        <div>
          <span className="text-xs text-gray-500">Geography</span>
          <p className="text-gray-800">{(edited.geographic_footprint || []).join(", ") || "—"}</p>
        </div>
        <div>
          <span className="text-xs text-gray-500">Estimated Revenue</span>
          <p className="text-gray-800">{edited.estimated_revenue_usd || "—"}</p>
        </div>
        <div>
          <span className="text-xs text-gray-500">India Connection</span>
          <p className="text-gray-800">{edited.india_connection || "None found"}</p>
        </div>
      </div>

      {edited.strategic_notes && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <p className="text-xs font-medium text-amber-700 mb-1">Strategic Notes</p>
          <p className="text-sm text-amber-900">{edited.strategic_notes}</p>
        </div>
      )}

      <button
        onClick={() => onConfirm(edited)}
        className="w-full py-2.5 bg-stone-800 text-white text-sm font-medium rounded-lg hover:bg-stone-700"
      >
        Confirm & Find Buyers
      </button>
    </div>
  );
}
