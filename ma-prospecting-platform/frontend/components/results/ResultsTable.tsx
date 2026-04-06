import { ScoredProspect } from "@/lib/types";
import { ProspectRow } from "./ProspectRow";

interface Props {
  prospects: ScoredProspect[];
}

export function ResultsTable({ prospects }: Props) {
  if (prospects.length === 0) {
    return <p className="text-sm text-gray-400 py-8 text-center">No prospects found.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
      <table className="w-full text-left">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            {["#", "Company", "Persona", "Sector", "Revenue", "Fit Score", "Top Signal", "Source", ""].map((col) => (
              <th key={col} className="px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {prospects.map((sp) => (
            <ProspectRow key={sp.prospect.id} sp={sp} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
