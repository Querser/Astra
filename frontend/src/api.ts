export type CrewMember = { id: string; display_name: string; fictional: boolean; archived_at: string | null; mission_location: "iss" | "moon" | "mars" | null; mission_phase: string | null; habitat: string | null };
export type SymptomReport = { id: string; description: string; observed_at: string; source_id: string; synthetic: boolean; withdrawn_at: string | null };
export type ComplaintReply = { symptom_report_id: string; recognized_symptom_codes: string[]; parsed_measurements: { id: string; metric: string; value: Observation["value"]; unit: string }[] };
export type ChatMessage = { id: string; crew_member_id: string; role: "user" | "assistant"; body: string; created_at: string; source_report_id: string | null; analysis_result_id: string | null; citations: string[]; legacy: boolean; engine?: string | null; request_id?: string | null };
export type ChatResponse = { crew_member_id: string; request_id: string; messages: ChatMessage[]; analysis: Analysis };
export type DataSource = { id: string; title: string; source_type: string; version: string | null };
export type MeasurementContext = {
  method?: string | null; device?: string | null; site?: string | null;
  activity_state?: string | null; posture?: string | null;
  mission_phase?: string | null; habitat?: string | null;
  subjective?: boolean | null; notes?: string | null;
  baseline_status?: "unknown" | "candidate" | "approved" | null;
};
export type Observation = {
  id: string; metric: string; value: { kind: "scalar"; amount: number } | { kind: "blood_pressure"; systolic: number; diastolic: number };
  unit: string; observed_at: string; synthetic: boolean; quality_flags: string[]; withdrawn_at: string | null;
  source_id: string;
  measurement_context?: MeasurementContext | null;
};
export type ReportItem = {
  statement?: string;
  explanation?: string;
  status?: string;
  source_title?: string;
  source_url?: string;
  category?: string;
  why?: string;
  condition?: string;
  escalation?: string;
  source_scope?: string;
  source_date?: string;
  sources?: { title: string; url: string }[];
  [key: string]: unknown;
};
export type ReferenceAssessment = {
  status: string;
  applicability?: string | null;
  scope?: string | null;
  source_title?: string | null;
  source_url?: string | null;
  reference_low?: number | null;
  reference_high?: number | null;
  reference_unit?: string | null;
  low?: number | null;
  high?: number | null;
  unit?: string | null;
  reason?: string | null;
  [key: string]: unknown;
};
export type PersonalSeriesAssessment = {
  status: string;
  count?: number;
  approved?: boolean;
  explanation?: string;
  limitation?: string;
  delta_from_previous?: number;
  [key: string]: unknown;
};
export type ParameterAssessment = {
  metric: string;
  value: Observation["value"] | number | null;
  unit: string | null;
  observed_at: string | null;
  source_id: string | null;
  entry_kind: string;
  acquisition_kind: string;
  synthetic: boolean;
  quality_flags: string[];
  quality_status: string;
  freshness_status: string;
  reference: ReferenceAssessment;
  personal_series: PersonalSeriesAssessment;
  series_insight?: { count: number; summary: string; first_median?: number; recent_median?: number; delta?: number; recent_min?: number; recent_max?: number; context_note?: string; source_url?: string };
  status: string;
  explanation: string;
  missing_context: string[];
  [key: string]: unknown;
};
export type IntegratedReport = {
  overall_assessment?: string;
  complaint_review?: {
    report_id: string; description: string; observed_at: string; recorded_at: string;
    source_id: string; source_type: string; source_title: string; synthetic: boolean;
    location?: string | null; recognized_symptoms: string[]; known: string[];
    unknowns: string[]; interpretation: string; status: string;
  }[];
  diagnostic_candidates?: {
    id: string; name: string; status: string; priority?: string; primary_metric: string; evidence: string; explanation: string;
    evidence_observation_ids: string[]; missing_confirmation: string[];
    sources: { title: string; url: string }[]; applicability: string;
  }[];
  coverage: (ReportItem & { observation_count?: number; parameter_count?: number; not_recorded_metrics?: string[]; synthetic_parameter_count?: number }) | null;
  observed_facts: (ReportItem | string)[];
  deterministic_findings: (ReportItem | string)[];
  possible_explanations: (ReportItem | string)[];
  unverified_hypotheses: (ReportItem | string)[];
  mission_environment_context: (ReportItem & { location?: string; name?: string; phase?: string; habitat?: string; gravity?: string; external_atmosphere?: string; radiation?: string; sources?: { title: string; url: string }[]; records?: { id: string; metric: string; value: number; unit: string; synthetic: boolean }[] }) | (ReportItem | string)[];
  next_steps: (ReportItem | string)[];
  condition_scenarios?: { candidate_id: string; candidate_name: string; follow: string; ignore: string; horizon: string; source_url: string; status: string }[];
  scenario_comparison: (ReportItem & { follow_recommendations?: string; ignore_recommendations?: string; uncertainty?: string; time_horizon?: string }) | null;
  uncertainty: (ReportItem | string)[];
  provenance: (ReportItem & { rule_set_version?: string; input_ids?: string[]; reference_source_urls?: string[]; knowledge_package_status?: string }) | null;
};
export type Analysis = {
  id: string;
  rule_set_version?: string;
  input_ids?: string[];
  created_at?: string;
  facts: Record<string, unknown>[];
  findings: Record<string, unknown>[];
  guidance: Record<string, unknown>[];
  hypotheses: Record<string, unknown>[];
  unknowns: Record<string, unknown>[];
  parameter_assessments?: ParameterAssessment[];
  integrated_report?: IntegratedReport | null;
};
export type Alert = { id: string; title: string; explanation: string; state: string };
export type AssistantReply = { status: string; answer: string; citations: string[]; model: string | null };
export type Forecast = {
  metric: string; horizon_hours: number; status: string; method: string | null;
  predicted_value: number | null; interval_low: number | null; interval_high: number | null;
  unit: string | null; insufficiency_reason: string | null; evaluation_mae: number | null;
  training_count: number; history_start_at?: string | null; history_end_at?: string | null;
  excluded_count?: number | null; synthetic_count?: number | null;
  evaluation_count?: number | null; baseline_mae?: number | null;
  interval_coverage?: number | null;
    recent_values?: number[]; selection_mae?: Record<string, number>;
};

export type MissionReadiness = {
  crew_member_id: string;
  status: string;
  statement: string;
  criteria_configured: boolean;
  criteria_version?: string | null;
  contributing_factors: { criterion_id: string; criterion: string; met: boolean; evidence: string }[];
  missing_data: string[];
  required_human_follow_up: boolean;
  criteria_scope?: string;
  criteria?: { id?: string; label?: string; status?: string; statement?: string }[];
};

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export function reportClientEvent(code: "api_failure" | "ui_exception" | "scenario_failure" | "form_failure", requestId?: string): void {
  // Only fixed event codes and a server-generated correlation ID leave the browser.
  void fetch(`${baseUrl}/client-events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, request_id: requestId ?? null }),
  }).catch(() => undefined);
}

export class ApiError extends Error {
  constructor(public readonly status: number, detail: string) { super(detail); }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    });
  } catch {
    reportClientEvent("api_failure");
    throw new Error("Local API is unavailable. Check that the server is running on port 8000.");
  }
  if (!response.ok) {
    reportClientEvent("api_failure", response.headers.get("X-Request-ID") ?? undefined);
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : `API Error ${response.status}`;
    throw new ApiError(response.status, detail);
  }
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>;
}

export function scalarValue(observation: Observation): number | null {
  return observation.value.kind === "scalar" ? observation.value.amount : null;
}
