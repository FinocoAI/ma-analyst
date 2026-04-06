import { BuyerPersona } from "@/lib/types";
import { PERSONA_LABELS, PERSONA_COLORS } from "@/lib/constants";

export function PersonaBadge({ persona }: { persona: BuyerPersona }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${PERSONA_COLORS[persona]}`}>
      {PERSONA_LABELS[persona]}
    </span>
  );
}
