export type BuyerPersona = "strategic" | "private_equity" | "conglomerate";
export type SignalType =
  | "acquisition_intent"
  | "sector_expansion"
  | "technology_gap"
  | "geographic_interest"
  | "capex_signal"
  | "board_action"
  | "product_mix_match";
export type SignalStrength = "high" | "medium" | "low";
export type PipelineStatus =
  | "created"
  | "profiling"
  | "profile_ready"
  | "prospecting"
  | "extracting_signals"
  | "scoring"
  | "complete"
  | "failed";

export type ScrapeContentQuality =
  | "high"
  | "curl_boost"
  | "exa_enriched"
  | "playwright"
  | "low";

export interface TargetProfile {
  company_name: string;
  url: string;
  description: string;
  sector_l1: string;
  sector_l2: string;
  sector_l3: string;
  key_technologies: string[];
  estimated_employees: number | null;
  estimated_revenue_usd: string | null;
  geographic_footprint: string[];
  years_in_operation: number | null;
  india_connection: string | null;
  strategic_notes: string;
  custom_guidance: string;
  /** How the backend obtained readable text for profiling */
  scrape_content_quality?: ScrapeContentQuality;
}

export interface Prospect {
  id: string;
  company_name: string;
  ticker: string | null;
  is_listed: boolean;
  persona: BuyerPersona;
  sector: string;
  sector_relevance: "exact_match" | "adjacent" | "tangential";
  product_mix_notes: string;
  estimated_revenue_inr_cr: number | null;
  estimated_revenue_usd_m: number | null;
  website_url: string | null;
  source: string;
  country: string;
}

export interface Signal {
  id: string;
  prospect_id: string;
  quote: string;
  signal_type: SignalType;
  strength: SignalStrength;
  source_document: string;
  source_quarter: string;
  source_url: string | null;
  source_context: string | null;
  reasoning: string;
}

export interface DimensionScore {
  dimension: string;
  score: number;
  weight: number;
  justification: string;
  supporting_quote: string | null;
  source: string | null;
}

export interface ScoredProspect {
  prospect: Prospect;
  signals: Signal[];
  dimension_scores: DimensionScore[];
  weighted_total: number;
  rank: number;
  top_signal: Signal | null;
  match_reasoning: string;
}

export interface ScoringWeights {
  sector_adjacency: number;
  technology_gap: number;
  geographic_strategy: number;
  financial_capacity: number;
  timing_signals: number;
  product_mix: number;
}

export interface UserFilters {
  personas: BuyerPersona[];
  revenue_min_usd_m: number | null;
  revenue_max_usd_m: number | null;
  geography: string;
  custom_signal_keywords: string[];
  num_results: number;
}

export interface PipelineStatusResponse {
  run_id: string;
  status: PipelineStatus;
  current_step: string;
  progress_pct: number;
  error_message: string | null;
  scrape_content_quality?: ScrapeContentQuality | null;
}

export interface ChatMessage {
  id: string;
  run_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}
