export type LLMReviewStatus = 'ok' | 'caution' | 'reject' | 'skipped' | 'failed';

export type LLMReviewSeverity = 'info' | 'warning' | 'critical';

export type LLMReviewIssue = {
  code: string;
  severity: LLMReviewSeverity;
  message: string;
  destination_id?: string | null;
  day?: number | null;
  item_id?: string | null;
};

export type LLMReviewAdjustment = {
  action:
    | 'demote'
    | 'promote'
    | 'remove'
    | 'swap'
    | 'regenerate'
    | 'replace_item'
    | 'adjust_time'
    | 'add_candidate_poi'
    | 'generate_external_route';
  reason: string;
  destination_id?: string | null;
  item_id?: string | null;
  replacement_id?: string | null;
  day?: number | null;
  payload?: Record<string, unknown> | null;
};

export type LLMCandidatePOI = {
  name: string;
  category?: string | null;
  lat?: number | null;
  lng?: number | null;
  address?: string | null;
  source_url?: string | null;
  official_url?: string | null;
  confidence?: number | null;
  evidence?: Record<string, unknown> | null;
};

export type LLMQualityReview = {
  review_id?: string | null;
  provider: string;
  model: string;
  prompt_version: string;
  status: LLMReviewStatus;
  issues: LLMReviewIssue[];
  suggested_adjustments: LLMReviewAdjustment[];
  user_summary_ru?: string | null;
  defense_trace?: string | null;
};
