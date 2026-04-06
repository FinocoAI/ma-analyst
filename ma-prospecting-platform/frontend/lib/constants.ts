import { ScoringWeights, UserFilters } from "./types";

export const DEFAULT_WEIGHTS: ScoringWeights = {
  sector_adjacency: 20,
  technology_gap: 20,
  geographic_strategy: 15,
  financial_capacity: 15,
  timing_signals: 15,
  product_mix: 15,
};

export const DEFAULT_FILTERS: UserFilters = {
  personas: ["strategic", "conglomerate"],
  revenue_min_usd_m: null,
  revenue_max_usd_m: null,
  geography: "India",
  custom_signal_keywords: [],
  num_results: 25,
};

export const PERSONA_LABELS: Record<string, string> = {
  strategic: "Strategic",
  private_equity: "Private Equity",
  conglomerate: "Conglomerate",
};

export const PERSONA_COLORS: Record<string, string> = {
  strategic: "bg-blue-100 text-blue-800",
  private_equity: "bg-purple-100 text-purple-800",
  conglomerate: "bg-amber-100 text-amber-800",
};

export const SIGNAL_STRENGTH_COLORS: Record<string, string> = {
  high: "text-green-600 bg-green-50 border-green-200",
  medium: "text-yellow-600 bg-yellow-50 border-yellow-200",
  low: "text-gray-500 bg-gray-50 border-gray-200",
};

export const DIMENSION_LABELS: Record<string, string> = {
  sector_adjacency: "Sector Adjacency",
  technology_gap: "Technology Gap",
  geographic_strategy: "Geographic Strategy",
  financial_capacity: "Financial Capacity",
  timing_signals: "Timing Signals",
  product_mix: "Product Mix",
};
