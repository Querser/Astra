import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useProfileChat } from "./useProfileChat";
import { Alert, Analysis, api, CrewMember, Forecast, MeasurementContext, MissionReadiness, Observation, ParameterAssessment, ReportItem, SymptomReport } from "./api";
import { ResearchSources, type ScienceCard } from "./ResearchSources";
import { Dashboard } from "./telemetry/Dashboard";
import { buildDashboardProfile, statusFromAnalysis } from "./telemetry/dashboard-data";

const metrics = [
  { id: "heart_rate", label: "Pulse", unit: "bpm", unitHelp: "bpm means beats per minute." },
  { id: "spo2", label: "SpO₂", unit: "%", unitHelp: "Percentage of oxygen saturation." },
  { id: "blood_pressure", label: "Blood pressure", unit: "mmHg", unitHelp: "Systolic and diastolic pressure in mmHg. Repeated readings on different days are needed to assess possible hypertension." },
  { id: "body_temperature", label: "Body Temperature", unit: "°C", unitHelp: "Degrees Celsius." },
  { id: "respiratory_rate", label: "Respiratory Rate", unit: "breaths/min", unitHelp: "Breathing Movements per Minute." },
  { id: "sleep_duration", label: "Sleep Duration", unit: "h", unitHelp: "Hours." },
  { id: "sleep_quality", label: "Sleep Self-Assessment", unit: "score", unitHelp: "Internal Scale 0–10: 10 — best sleep quality. This is not a clinical threshold." },
  { id: "activity", label: "Activity", unit: "steps", unitHelp: "Steps per day; compared to personal history. Steps are not equal to minutes of moderate activity." },
  { id: "exertion_fatigue", label: "Fatigue", unit: "score", unitHelp: "Internal Scale 0–10: 10 — stronger fatigue. This is not a clinical threshold." },
];
function localNowForApi() { const now = new Date(); const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16); return localDateTimeWithOffset(local); }
function localDateTimeWithOffset(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) throw new Error("Check the date and time of measurement.");
  const offset = -date.getTimezoneOffset();
  const sign = offset < 0 ? "-" : "+";
  return `${value}:00${sign}${String(Math.floor(Math.abs(offset) / 60)).padStart(2, "0")}:${String(Math.abs(offset) % 60).padStart(2, "0")}`;
}
function optionalText(data: FormData, key: string): string | null { return String(data.get(key) ?? "").trim() || null; }
function measurementContextText(context?: MeasurementContext | null): string {
  if (!context) return "Conditions not specified";
  const parts = [context.method, context.device, context.site, context.activity_state, context.posture, context.mission_phase, context.habitat].filter(Boolean);
  return parts.length ? parts.join(" · ") : "Conditions not specified";
}
function ChatSources({ citations, cards }: { citations: string[]; cards: ScienceCard[] }) {
  const science = [...new Set(citations.filter(ref => ref.startsWith("ASTRA_SPACE_SCIENCE.json#")))].map(ref => cards.find(card => card.id === ref.split("#")[1])).filter((card): card is ScienceCard => Boolean(card));
  const research = citations.some(ref => ref.startsWith("research:"));
  const local = citations.some(ref => ref.startsWith("ASTRA_CHAT_CASES.json#") || ref.startsWith("ASTRA_DEMO_GUIDANCE.json#"));
  const original = [...new Set(citations.filter(ref => ref.startsWith("source:https://")))];
  if (!science.length && !research && !local) return null;
  return <div className="chat-sources"><span>Sources:</span>{science.map(card => <a key={card.id} href={card.source?.url ?? card.source_url} target="_blank" rel="noreferrer" title={card.source?.title ?? card.source_title}>{card.source?.organization ?? card.source_organization ?? "Scientific Reference"} · {card.title_ru ?? card.title ?? card.id}{card.source?.section ? ` · ${card.source.section}` : ""}</a>)}{research && <a href="#workspace-research">Archival and research data · sources</a>}{local && <span>Local ASTRA database</span>}{original.map((ref, index) => <a key={ref} href={ref.slice(7)} target="_blank" rel="noreferrer">Original source {index + 1} ↗</a>)}</div>;
}
function MeasurementContextFields({ metric }: { metric: string }) {
  return <details className="measurement-conditions"><summary>Measurement conditions (if possible)</summary>
    <p className="muted">Specify conditions if you know them. Empty time means the moment of saving. For old records unknown conditions remain unknown.</p>
    <div className="measurement-fields">
      <label>When measured<input name="observed_at_local" type="datetime-local" /></label>
      <label>Method<input name="method" maxLength={80} placeholder={metric === "body_temperature" ? "For example, thermometer" : "For example, manual count"} /></label>
      <label>Instrument<input name="device" maxLength={80} placeholder="Name or type, if known" /></label>
      <label>Measurement location<input name="site" maxLength={80} placeholder={metric === "body_temperature" ? "Armpit area" : "If applicable"} /></label>
      <label>State<select name="activity_state" defaultValue=""><option value="">Unknown</option><option value="rest">Rest</option><option value="activity">After Load</option><option value="sleep">Sleep</option></select></label>
      <label>Body Position<select name="posture" defaultValue=""><option value="">Unknown</option><option value="sitting">Sitting</option><option value="standing">Standing</option><option value="lying">Lying</option></select></label>
      <label>Record Type<select name="subjective" defaultValue={metric === "sleep_quality" || metric === "exertion_fatigue" ? "true" : "false"}><option value="false">Instrument Reading or Count</option><option value="true">Self-assessment</option><option value="">Unknown</option></select></label>
      <label>Baseline series<select name="baseline_status" defaultValue="unknown"><option value="unknown">Not set</option><option value="candidate">Comparison candidate</option><option value="approved">Approved separately</option></select></label>
      <label className="measurement-notes">Note<input name="notes" maxLength={500} placeholder="For example, immediately after training" /></label>
    </div>
  </details>;
}
function ObservationRevisionForm({ observation, onDone, onCancel }: { observation: Observation; onDone: () => Promise<void>; onCancel: () => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const revise = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const value = observation.value.kind === "blood_pressure"
      ? { kind: "blood_pressure", systolic: Number(data.get("systolic")), diastolic: Number(data.get("diastolic")) }
      : { kind: "scalar", amount: Number(data.get("amount")) };
    const measurement_context: MeasurementContext = { ...observation.measurement_context,
      method: optionalText(data, "method"), device: optionalText(data, "device"), site: optionalText(data, "site"),
      activity_state: optionalText(data, "activity_state"), posture: optionalText(data, "posture"), notes: optionalText(data, "notes"),
    };
    try {
      setBusy(true); setError("");
      await api<Observation>(`/observations/${observation.id}`, { method: "PATCH", body: JSON.stringify({
        metric: observation.metric, value, unit: data.get("unit"), observed_at: observation.observed_at,
        source_id: observation.source_id, synthetic: observation.synthetic, quality_flags: observation.quality_flags, measurement_context,
      }) });
      await onDone();
    } catch (reason) { setError(String(reason)); } finally { setBusy(false); }
  };
  return <form className="measurement-revision" onSubmit={revise}>
    <strong>Correction of entry · {formatDate(observation.observed_at)}</strong>
    <div className="measurement-fields">
      {observation.value.kind === "blood_pressure" ? <><label>Systolic<input name="systolic" type="number" step="any" defaultValue={observation.value.systolic} required /></label><label>Diastolic<input name="diastolic" type="number" step="any" defaultValue={observation.value.diastolic} required /></label></> : <label>Value<input name="amount" type="number" step="any" defaultValue={observation.value.amount} required /></label>}
      <label>Unit<input name="unit" defaultValue={observation.unit} required /></label>
      <label>Method<input name="method" defaultValue={observation.measurement_context?.method ?? ""} /></label>
      <label>Instrument<input name="device" defaultValue={observation.measurement_context?.device ?? ""} /></label>
      <label>Measurement location<input name="site" defaultValue={observation.measurement_context?.site ?? ""} /></label>
      <label>State<select name="activity_state" defaultValue={observation.measurement_context?.activity_state ?? ""}><option value="">Unknown</option><option value="rest">Rest</option><option value="activity">After Load</option><option value="sleep">Sleep</option></select></label>
      <label>Position<select name="posture" defaultValue={observation.measurement_context?.posture ?? ""}><option value="">Unknown</option><option value="sitting">Sitting</option><option value="standing">Standing</option><option value="lying">Lying</option></select></label>
      <label>Note<input name="notes" defaultValue={observation.measurement_context?.notes ?? ""} /></label>
    </div>
    {error && <p role="alert">{error}</p>}
    <div className="revision-actions"><button disabled={busy}>Save Correction</button><button type="button" onClick={onCancel} disabled={busy}>Cancel</button></div>
  </form>;
}

function findingText(item: Record<string, unknown>): string {
  if (item.rule_id === "quality_flags_present") return `Check the quality of records: label «${String(item.quality_flag)}» for ${String(item.affected_observations)} measurements. Clinical significance is not established.`;
  if (item.rule_id === "unit_mismatch") return `The indicator «${metricLabel(String(item.metric))}» has different units of measurement: ${Array.isArray(item.units) ? item.units.join(", ") : "unknown"}. Comparison of numbers is missing.`;
  if (item.rule_id === "reference_comparison") return `${metricLabel(String(item.metric))}: ${formatNumber(item.value)} ${unitLabel(item.unit)} ${item.status === "below_reference" ? "below" : "above"} published landmark. Measurement conditions and mission applicability are not confirmed.`;
  if (item.rule_id === "coincident_oxygen_breathing") return "Decreased SpO₂ and increased respiratory rate are entered with an interval of up to 30 minutes. This is a combined observation, not an established cause or diagnosis.";
  if (item.rule_id === "descriptive_series_change") return `Last measurement "${String(item.metric)}" differs from the previous series. This is a statistical observation, not a diagnosis.`;
  return String(item.statement ?? "Change detected in the data.");
}

function metricLabel(id: string): string { return metrics.find((item) => item.id === id)?.label ?? id; }
function formatNumber(value: unknown): string { return typeof value === "number" ? new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 }).format(value) : "—"; }
function formatForecastNumber(metric: string, value: number): string {
  const digits = metric === "activity" || metric === "heart_rate" || metric === "respiratory_rate" ? 0 : 1;
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(value);
}
function unitLabel(value: unknown, amount?: number): string {
  const unit = String(value ?? "");
  if ((unit === "score" || unit === "steps") && typeof amount === "number" && Number.isInteger(amount)) {
    const singular = unit === "score" ? "point" : "step";
    const paucal = unit === "score" ? "points" : "steps";
    const plural = unit === "score" ? "points" : "steps";
    const lastTwo = Math.abs(amount) % 100;
    const last = Math.abs(amount) % 10;
    return lastTwo >= 11 && lastTwo <= 14 ? plural : last === 1 ? singular : last >= 2 && last <= 4 ? paucal : plural;
  }
  return ({ bpm: "beats/min", "breaths/min": "breaths/min", h: "h", steps: "steps", score: "points", mmHg: "mmHg" } as Record<string, string>)[unit] ?? unit;
}
function latestValue(item: Record<string, unknown>): string {
  const value = item.latest_value as { kind?: string; amount?: number; systolic?: number; diastolic?: number } | undefined;
  if (value?.kind === "scalar") return `${formatNumber(value.amount)} ${unitLabel(item.unit)}`;
  if (value?.kind === "blood_pressure") return `${formatNumber(value.systolic)}/${formatNumber(value.diastolic)} ${unitLabel(item.unit)}`;
  return "—";
}
function comparisonText(item: Record<string, unknown>): string {
  if (item.comparison_status === "mixed_units") return "Different units: numerical comparison is missing.";
  if (item.comparison_status === "single_point") return "One point: personal dynamics cannot be assessed.";
  const delta = item.delta_from_previous;
  const change = typeof delta === "number" ? `Difference from previous: ${delta > 0 ? "+" : ""}${formatNumber(delta)} ${unitLabel(item.unit)}. ` : "";
  return `${change}Range: ${formatNumber(item.minimum)}–${formatNumber(item.maximum)} ${unitLabel(item.unit)}; median: ${formatNumber(item.median)}.`;
}

function referenceText(item: Record<string, unknown> | undefined): string {
  if (!item) return "Comparison not performed.";
  const status = String(item.status);
  if (status === "not_assessed") {
    const reasons: Record<string, string> = {
      measurement_method_not_recorded: "Measurement method for temperature is not specified.",
      rating_scale_not_defined: "Self-assessment scale is not defined.",
      measurement_period_not_recorded: "Period for step count is not specified.",
      unit_not_comparable: "Unit does not match the reference range.",
      separate_pressure_rule_not_configured: "Earth reference range is not used here; repeated values are evaluated by a separate rule below.",
    };
    return reasons[String(item.reason)] ?? "No suitable reference range.";
  }
  const range = item.reference_high == null
    ? `from ${formatNumber(item.reference_low)} ${unitLabel(item.reference_unit)}`
    : `${formatNumber(item.reference_low)}–${formatNumber(item.reference_high)} ${unitLabel(item.reference_unit)}`;
  const qualifier = item.context === "adult_at_rest" ? "for adult at rest" : item.metric === "sleep_duration" ? "for adult per day" : "for most healthy people";
  const result = status === "below_reference" ? "Below" : status === "above_reference" ? "Above" : "Within";
  return `${result} reference range ${range} ${qualifier}.`;
}

function guidanceText(item: Record<string, unknown>): string {
  if (item.kind === "verify_oxygen_reading") return "If the reading is real: recheck the sensor and measurement. If the value remains low or symptoms occur without delay, contact a qualified healthcare professional.";
  if (item.kind === "verify_resting_context") return `For ${metricLabel(String(item.metric))}» check the unit, input, and whether the measurement was taken at rest. If the deviation repeats or symptoms are present, a specialist evaluation is needed.`;
  if (item.kind === "sleep_habits") return "Check sleep pattern and quality; regular sleep time and a quiet, cool environment are CDC recommendations.";
  return String(item.statement ?? "Check the measurement conditions.");
}
function hypothesisText(item: Record<string, unknown>): string {
  if (item.kind === "possible_low_oxygen") return "Low oxygen content is possible only with confirmed low SpO₂. A single unverified reading does not establish a cause or diagnosis.";
  return String(item.statement ?? "Working hypothesis requires verification.");
}

function limitationText(item: Record<string, unknown>): string {
  if (item.kind === "mission_reference") return "General Earth-based references for adults have been used. They cannot be automatically applied to space mission conditions or considered personal norms.";
  if (item.kind === "collection_schedule") return "No measurement schedule is specified, so the program cannot assess missed or outdated records.";
  if (item.kind === "personal_history") return `For ${String(item.metric_count)} readings there is only one measurement; comparison with personal history is not yet possible.`;
  if (item.kind === "measurement_context") return "No rest or load, symptoms, device, or environmental conditions are specified. These numbers alone cannot establish a cause or severity of the condition.";
  return String(item.statement ?? "Analysis limitation.");
}

function parameterValue(item: ParameterAssessment): string {
  if (typeof item.value === "number") return `${formatNumber(item.value)} ${unitLabel(item.unit, item.value)}`;
  if (item.value && typeof item.value === "object") {
    if (item.value.kind === "scalar") return `${formatNumber(item.value.amount)} ${unitLabel(item.unit, item.value.amount)}`;
    if (item.value.kind === "blood_pressure") return `${formatNumber(item.value.systolic)}/${formatNumber(item.value.diastolic)} ${unitLabel(item.unit)}`;
  }
  return "No comparable value";
}

function assessmentStatus(status: string): string {
  const names: Record<string, string> = {
    within_reference: "Within the conditional reference",
    within_available_reference: "Within the conditional reference",
    meets_minimum: "Matches the reference minimum",
    below_reference: "Below the conditional reference",
    above_reference: "Above the conditional reference",
    outside_available_reference: "Beyond the conditional reference",
    diagnostic_candidate: "Named diagnostic candidate",
    changed_from_baseline: "Change relative to personal series",
    changed_from_personal_series: "Descriptive change in personal series",
    descriptive_change: "Descriptive change in the series",
    descriptive_only: "Only descriptive series",
    descriptive_trend: "Dynamic by personal history",
    insufficient_history: "Not enough history",
    conflicting_units: "Incompatible units",
    stale: "Old record",
    missing: "No data",
    conflicting: "Data contradict each other",
    invalid: "Incorrect record",
    insufficient_evidence: "Not enough data",
    not_assessed: "Comparison not performed",
    unavailable: "Not available",
  };
  return names[status] ?? (status ? status.replaceAll("_", " ") : "Not assessed");
}

function acquisitionText(item: ParameterAssessment): string {
  if (item.synthetic) return "Synthetic record";
  const kind = item.acquisition_kind || item.entry_kind;
  const names: Record<string, string> = {
    manual: "Manual input",
    measured: "Measurement",
    sensor: "Sensor",
    self_reported: "From Human Statement",
    self_report: "From Human Statement",
    derived: "Calculated Indicator",
    imported: "Import",
    import: "Import",
    unknown: "Origin Not Determined",
  };
  return names[kind] ?? "Method of Acquisition Requires Clarification";
}

function qualityText(status: string): string {
  const names: Record<string, string> = {
    unflagged: "no quality flags", flagged: "has quality flag",
    declared_invalid: "record declared as unreliable", declared_stale: "record marked as obsolete",
    conflicting_units: "incompatible units",
  };
  return names[status] ?? "quality requires verification";
}

function missingContextText(code: string): string {
  const names: Record<string, string> = {
    measurement_method: "method of measurement", mission_phase: "mission phase",
    approved_personal_baseline: "approved initial series",
    rest_or_activity_state: "rest or load", device_and_signal_quality: "device and signal quality",
  };
  return names[code] ?? code.replaceAll("_", " ");
}

function referenceAssessmentText(item: ParameterAssessment): string {
  const reference = item.reference;
  if (!reference || reference.status === "not_assessed" || reference.status === "insufficient_evidence") return "There is no universal numeric clinical threshold for this unit; personal dynamics are shown";
  if (reference.status.startsWith("bp_")) return `Earth category: ${String(reference.description_ru ?? "not specified")}`;
  if (reference.status === "below_fever_threshold" || reference.status === "at_or_above_fever_threshold") return "Reference high temperature in adults: 38 °C; method and location of measurement should be considered";
  const low = reference.low ?? reference.reference_low;
  const high = reference.high ?? reference.reference_high;
  const unit = reference.unit ?? reference.reference_unit ?? item.unit;
  const limits = low == null ? "" : high == null
    ? ` from ${formatNumber(low)} ${unitLabel(unit)}`
    : ` ${formatNumber(low)}–${formatNumber(high)} ${unitLabel(unit)}`;
  return `${assessmentStatus(reference.status)}${limits}`;
}

function personalSeriesText(item: ParameterAssessment): string {
  const series = item.personal_series;
  if (!series) return "Personal series not available";
  const count = typeof series.count === "number" ? series.count : 0;
  if (count < 2) return `${count} record; dynamics unavailable`;
  if (series.status === "conflicting_units") return `${count} records; comparison not possible due to units`;
  const delta = typeof series.delta_from_previous === "number" ? `; to previous: ${series.delta_from_previous > 0 ? "+" : ""}${formatNumber(series.delta_from_previous)} ${unitLabel(item.unit)}` : "";
  const pressureDelta = typeof series.systolic_delta_from_previous === "number" && typeof series.diastolic_delta_from_previous === "number"
    ? `; to previous: ${formatNumber(series.systolic_delta_from_previous)}/${formatNumber(series.diastolic_delta_from_previous)} mm Hg` : "";
  const change = series.status === "descriptive_change" ? "; significant change in the series" : "";
  return `${count} records${delta}${pressureDelta}${change}`;
}

function reportItemText(item: ReportItem | string): string {
  if (typeof item === "string") return item;
  if (typeof item.statement === "string") return typeof item.candidate_name === "string" ? `${item.candidate_name}: ${item.statement}` : item.statement;
  if (typeof item.explanation === "string") return item.explanation;
  return typeof item.status === "string" ? assessmentStatus(item.status) : "Details not available.";
}

function ReportList({ items, empty }: { items: (ReportItem | string)[] | undefined; empty: string }) {
  if (!items?.length) return <p className="muted">{empty}</p>;
  return <ul>{items.map((item, index) => <li key={index}>{reportItemText(item)}</li>)}</ul>;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "unknown";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "unknown" : date.toLocaleString("en-US");
}

function forecastMethod(method: string | null): string {
  return ({ persistence: "last observation", recent_median: "median of 7 last points", robust_trend: "stable trend of 10 last points" } as Record<string, string>)[method ?? ""] ?? "method not defined";
}

function forecastReason(reason: string | null): string {
  if (!reason) return "For this horizon, there are not enough comparable data.";
  if (/[\u0400-\u04FF]/.test(reason)) return "This forecast cannot be calculated from the available comparable records.";
  if (/mixed units/i.test(reason)) return "Units of measurement differ; forecast without a validated conversion rule is not possible.";
  if (/seven.days|history|span/i.test(reason)) return "History of measurements is too short for this horizon; continue recording the indicator under the same conditions.";
  return "Insufficient comparable observations and error checks for this horizon.";
}

function forecastHorizon(hours: number): string {
  return ({ 24: "24 hours", 72: "72 hours", 168: "7 days" } as Record<number, string>)[hours] ?? `${hours} h`;
}

function readinessStatus(status: string): string {
  return ({ meets_configured_criteria: "Matches configured criteria", conditional_review: "Conditional - requires verification", does_not_meet_configured_criteria: "Does not match configured criteria", not_assessed: "Not assessed" } as Record<string, string>)[status] ?? "Assessment requires verification";
}

function actionCategory(category: string | undefined): string {
  return ({ educational_information: "Educational information", information: "Educational information", data_collection: "Data clarification", collect_more_data: "Data clarification", first_aid: "First aid", escalation: "Forward to responsible medic", contact_medical_officer: "Forward to responsible medic" } as Record<string, string>)[category ?? ""] ?? "Next step";
}

function symptomName(value: string): string {
  return ({ external_bleeding: "External bleeding", head_impact: "Head impact", headache: "Headache", nausea: "Nausea", vomiting: "Vomiting", loud_snoring: "Loud snoring", witnessed_breathing_pauses: "Sleep apnea reported by witness", daytime_sleepiness: "Daytime sleepiness", dyspnea: "Difficult breathing", chest_pain: "Chest pain", vision_change: "Vision changes" } as Record<string, string>)[value] ?? value;
}

function RecommendationList({ items }: { items: (ReportItem | string)[] }) {
  if (!items.length) return <p className="muted">There are no confirmed steps for these data in the current rules.</p>;
  const unique = items.filter((item, index) => items.findIndex((other) => reportItemText(other) === reportItemText(item)) === index);
  return <ol className="recommendation-list">{unique.map((item, index) => {
    if (typeof item === "string") return <li key={index}>{item}</li>;
    const category = typeof item.category === "string" ? item.category : typeof item.kind === "string" ? item.kind : undefined;
    const urgent = category === "escalation" || category === "first_aid";
    return <li key={index} className="recommendation-step"><span className="recommendation-type">{actionCategory(category)}</span><strong>{item.statement ?? "Action requires clarification"}</strong>{typeof item.condition === "string" && <p><span className="muted">Condition:</span> {item.condition}</p>}{urgent && typeof item.escalation === "string" && <p><span className="muted">Escalation:</span> {item.escalation}</p>}<details><summary>Justification</summary>{typeof item.why === "string" && <p>{item.why}</p>}{!urgent && typeof item.escalation === "string" && <p>Escalation: {item.escalation}</p>}{item.source_scope && <p className="muted">{item.source_scope}</p>}</details></li>;
  })}</ol>;
}

function ForecastCards({ forecasts, parameter, latestValue }: { forecasts: Forecast[]; parameter: string; latestValue: number | null }) {
  if (!forecasts.length) return <p className="muted">Select a metric and run the calculation. Numbers will appear only for horizons with sufficient history and error check.</p>;
  return <div className="forecast-grid">{([24, 72, 168] as const).map((hours) => {
    const item = forecasts.find((entry) => entry.horizon_hours === hours);
    const selection = item?.selection_mae ?? {};
    const scores = Object.entries(selection).sort((a, b) => a[1] - b[1]);
    return <div className="forecast-card" key={hours}>
      <h4>{forecastHorizon(hours)}</h4>
      <p className="muted">{metricLabel(item?.metric ?? parameter)} · {item?.training_count ?? 0} measurements{item?.history_start_at && item.history_end_at ? ` · ${formatDate(item.history_start_at)} — ${formatDate(item.history_end_at)}` : ""}</p>
      {item?.recent_values?.length ? <p><strong>Last points:</strong> {item.recent_values.map((value) => formatForecastNumber(item.metric, value)).join(" → ")} {unitLabel(item.unit)}.</p> : null}
      {item?.status === "available" && item.predicted_value != null ? <>
        <p className="forecast-value">{formatForecastNumber(item.metric, item.predicted_value)} {unitLabel(item.unit)}</p>
        {latestValue != null && <p className="muted">From the last value: {item.predicted_value - latestValue > 0 ? "+" : ""}{formatForecastNumber(item.metric, item.predicted_value - latestValue)} {unitLabel(item.unit)}.</p>}
        <p>Method: <strong>{forecastMethod(item.method)}</strong>. {item.method === "persistence" ? "Takes the last point." : item.method === "recent_median" ? "Takes the median value of the last seven points; a single outlier does not shift the result." : "Median of pairwise slopes of the last ten points is transferred to the selected horizon."}</p>
        {scores.length > 0 && <p className="muted">Selection based on recent past points until individual check (mean error): {scores.map(([name, value]) => `${forecastMethod(name)} — ${formatNumber(value)} ${unitLabel(item.unit)}`).join("; ")}.</p>}
        <p className="muted">Individual check on {item.evaluation_count ?? 0} past points: error {item.evaluation_mae == null ? "not calculated" : `${formatNumber(item.evaluation_mae)} ${unitLabel(item.unit)}`}; reference of the last value — {item.baseline_mae == null ? "not calculated" : `${formatNumber(item.baseline_mae)} ${unitLabel(item.unit)}`}.</p>
        <p>{item.interval_low != null && item.interval_high != null ? `Range by errors of past calculations: ${formatForecastNumber(item.metric, item.interval_low)}–${formatForecastNumber(item.metric, item.interval_high)} ${unitLabel(item.unit)}.` : "Range not calculated: few individual points for error check."}</p>
        {item.evaluation_mae != null && item.baseline_mae != null && item.evaluation_mae > item.baseline_mae && <p className="forecast-insufficient">On individual check points selected method is worse than simple reference. This forecast is unreliable.</p>}
      </> : <p className="forecast-insufficient">Not enough data: {forecastReason(item?.insufficiency_reason ?? null)}</p>}
      {item?.synthetic_count ? <p className="muted">Training records: {item.synthetic_count}. The verification error does not show accuracy for real people.</p> : null}
      {item?.excluded_count ? <p className="muted">Excluded by quality or type: {item.excluded_count}.</p> : null}
    </div>;
  })}</div>;
}

function useOwnedValue<T>(owner: string, initial: T) {
  const [values, setValues] = useState<Record<string, T>>({});
  const set = (value: T) => setValues(old => ({ ...old, [owner]: value }));
  return [values[owner] ?? initial, set] as const;
}

export function App() {
  const [crew, setCrew] = useState<CrewMember[]>([]);
  const [scienceCards, setScienceCards] = useState<ScienceCard[]>([]);
  const [selectedCrew, selectCrew] = useState("");
  const setSelectedCrew = (id: string) => {
    sessionStorage.setItem("astra.crew", id);
    selectCrew(id);
  };
  const versions = useRef(new Map<string, number>());
  const version = (id: string) => versions.current.get(id) ?? 0;
  const invalidate = (id: string) => versions.current.set(id, version(id) + 1);
  const [observations, setObservations] = useOwnedValue<Observation[]>(selectedCrew, []);
  const [symptoms, setSymptoms] = useOwnedValue<SymptomReport[]>(selectedCrew, []);
  const [medicalHistory, setMedicalHistory] = useOwnedValue<import("./telemetry/dashboard-data").MedicalEpisode[]>(selectedCrew, []);
  const [crewAnalyses, setCrewAnalyses] = useState<Record<string, Analysis>>({});
  const [alerts, setAlerts] = useOwnedValue<Alert[]>(selectedCrew, []);
  const analysis = crewAnalyses[selectedCrew] ?? null;
  const receiveAnalysis = (id: string, next: Analysis) => {
    setCrewAnalyses(current => {
      const previous = current[id];
      if (previous?.created_at && next.created_at && previous.created_at > next.created_at) return current;
      return { ...current, [id]: next };
    });
  };
  const profileChat = useProfileChat(selectedCrew, (owner, next) => {
    invalidate(owner);
    receiveAnalysis(owner, next);
    // Reload only the records associated with this submit's originating profile.
    void reloadRecords(owner).catch(error => setMessage(String(error)));
  });
  const { rows: chat, draft: chatDraft, busy: chatBusy } = profileChat.state;
  const setChatDraft = profileChat.draft;
  const sendChatMessage = profileChat.send;
  const [forecastMetric, setForecastMetric] = useState("spo2");
  const [forecasts, setForecasts] = useOwnedValue<Forecast[]>(selectedCrew + "/" + forecastMetric, []);
  const [readiness, setReadiness] = useOwnedValue<MissionReadiness | null>(selectedCrew, null);
  const [message, setMessage] = useOwnedValue(selectedCrew, "");
  const [metric, setMetric] = useState("heart_rate");
  const [unit, setUnit] = useState("bpm");
  const [editingObservation, setEditingObservation] = useState<string | null>(null);
  const [showWorkspace, setShowWorkspace] = useState(false);
  const [workspaceTarget, setWorkspaceTarget] = useState<"crew" | "observation" | "complaint" | "report">("report");
  const selectedName = crew.find((item) => item.id === selectedCrew)?.display_name ?? "profile not selected";
  const selectedProfile = crew.find((item) => item.id === selectedCrew);
  const metricInfo = metrics.find((item) => item.id === metric) ?? metrics[0];

  const reload = async (preferred?: string) => {
    try {
      const nextCrew = await api<CrewMember[]>("/crew");
      setCrew(nextCrew);
      const desired = preferred ?? sessionStorage.getItem("astra.crew");
      setSelectedCrew(nextCrew.some(item => item.id === desired) ? desired! : nextCrew[0]?.id ?? "");
      setMessage("Local API is available.");
      const summaries = await Promise.allSettled(nextCrew.map((member) => api<Analysis>("/analysis/run", { method: "POST", body: JSON.stringify({ crew_member_id: member.id }) })));
      summaries.forEach((result, index) => { if (result.status === "fulfilled") receiveAnalysis(nextCrew[index].id, result.value); });
    } catch (error) { setMessage(error instanceof Error ? error.message : "API is unavailable."); }
  };
  const reloadRecords = async (crewId = selectedCrew) => {
    if (!crewId) return;
    const sequence = version(crewId);
    const [nextObservations, nextAlerts, nextSymptoms, nextReadiness, nextMemory] = await Promise.all([
      api<Observation[]>(`/observations?crew_member_id=${crewId}&current_only=true&limit=100`), api<Alert[]>(`/alerts?crew_member_id=${crewId}`), api<SymptomReport[]>(`/symptoms?crew_member_id=${crewId}&limit=100`),
      api<MissionReadiness>(`/mission-readiness/${crewId}`).catch(() => null),
      api<{ medical_history?: import("./telemetry/dashboard-data").MedicalEpisode[] }>(`/assistant/chat/${crewId}/memory`).catch(() => ({ medical_history: [] })),
    ]);
    if (sequence !== version(crewId)) return;
    setObservations(nextObservations); setAlerts(nextAlerts); setSymptoms(nextSymptoms); setReadiness(nextReadiness); setMedicalHistory(nextMemory.medical_history ?? []);
  };
  useEffect(() => { void reload(); void api<ScienceCard[]>("/reference/space-science").then(setScienceCards).catch(() => undefined); }, []);
  useEffect(() => {
    if (!selectedCrew) return;
    const sequence = version(selectedCrew);
    let cancelled = false;
    const loadOverview = async () => {
      try {
        const nextAnalysis = await api<Analysis>("/analysis/run", { method: "POST", body: JSON.stringify({ crew_member_id: selectedCrew }) });
        const [nextObservations, nextAlerts, nextSymptoms, nextReadiness, nextMemory] = await Promise.all([
          api<Observation[]>(`/observations?crew_member_id=${selectedCrew}&current_only=true&limit=100`),
          api<Alert[]>(`/alerts?crew_member_id=${selectedCrew}`),
          api<SymptomReport[]>(`/symptoms?crew_member_id=${selectedCrew}&limit=100`),
          api<MissionReadiness>(`/mission-readiness/${selectedCrew}`).catch(() => null),
          api<{ medical_history?: import("./telemetry/dashboard-data").MedicalEpisode[] }>(`/assistant/chat/${selectedCrew}/memory`).catch(() => ({ medical_history: [] })),
        ]);
        if (!cancelled && version(selectedCrew) === sequence) { receiveAnalysis(selectedCrew, nextAnalysis); setObservations(nextObservations); setAlerts(nextAlerts); setSymptoms(nextSymptoms); setReadiness(nextReadiness); setMedicalHistory(nextMemory.medical_history ?? []); }
      } catch (error) { if (!cancelled) setMessage(String(error)); }
    };
    void loadOverview();
    return () => { cancelled = true; };
  }, [selectedCrew]);
  useEffect(() => {
    if (!showWorkspace || !selectedCrew) return;
    let cancelled = false;
    void api<Forecast[]>("/forecasts/run", { method: "POST", body: JSON.stringify({ crew_member_id: selectedCrew, metric: forecastMetric }) })
      .then((value) => { if (!cancelled) setForecasts(value); })
      .catch((error) => { if (!cancelled) setMessage(String(error)); });
    return () => { cancelled = true; };
  }, [selectedCrew, forecastMetric, showWorkspace, analysis?.id]);

  const visibleObservations = useMemo(() => observations.filter((item) => item.metric === metric), [observations, metric]);
  const submitCrew = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const form = event.currentTarget; const name = new FormData(form).get("name");
    try { const created = await api<CrewMember>("/crew", { method: "POST", body: JSON.stringify({ display_name: name }) }); setSelectedCrew(created.id); form.reset(); await reload(created.id); } catch (error) { setMessage(String(error)); }
  };
  const submitObservation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const form = event.currentTarget; if (!selectedCrew) { setMessage("First create or select a profile."); return; }
    const data = new FormData(form);
    try {
      const value = metric === "blood_pressure"
        ? { kind: "blood_pressure", systolic: Number(data.get("systolic")), diastolic: Number(data.get("diastolic")) }
        : { kind: "scalar", amount: Number(data.get("amount")) };
      const localTime = optionalText(data, "observed_at_local");
      const observedAt = localTime ? localDateTimeWithOffset(localTime) : localNowForApi();
      const measurement_context: MeasurementContext = {
        method: optionalText(data, "method"), device: optionalText(data, "device"), site: optionalText(data, "site"),
        activity_state: optionalText(data, "activity_state"), posture: optionalText(data, "posture"),
        mission_phase: selectedProfile?.mission_phase ?? null, habitat: selectedProfile?.habitat ?? null,
        subjective: data.get("subjective") === "" ? null : data.get("subjective") === "true",
        baseline_status: (data.get("baseline_status") || "unknown") as MeasurementContext["baseline_status"],
        notes: optionalText(data, "notes"),
      };
      await api<Observation>("/manual/observations", { method: "POST", body: JSON.stringify({ crew_member_id: selectedCrew, metric, value, unit: data.get("unit"), observed_at: observedAt, measurement_context }) });
      form.reset(); invalidate(selectedCrew); setForecasts([]); setAlerts([]); setMessage("Measurement saved; updating overview…"); await runAnalysis();
    } catch (error) { setMessage(String(error)); }
  };
  const submitMission = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!selectedCrew) return;
    const data = new FormData(event.currentTarget);
    const location = String(data.get("mission_location"));
    try {
      await api<CrewMember>(`/crew/${selectedCrew}/mission`, { method: "PATCH", body: JSON.stringify({ mission_location: location, mission_phase: location === "iss" ? "orbit" : "surface", habitat: data.get("habitat") }) });
      setCrew(await api<CrewMember[]>("/crew"));
      await runAnalysis();
      setMessage("Mission context updated.");
    } catch (error) { setMessage(String(error)); }
  };
  const sendChat = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); void sendChatMessage(chatDraft.trim()); };
  const runAnalysis = async (): Promise<Analysis | null> => { if (!selectedCrew) return null; try { const next = await api<Analysis>("/analysis/run", { method: "POST", body: JSON.stringify({ crew_member_id: selectedCrew }) }); receiveAnalysis(selectedCrew, next); await reloadRecords(); setMessage("Overview updated."); return next; } catch (error) { setMessage(String(error)); return null; } };
  const runForecast = async () => { if (!selectedCrew) return; try { setForecasts(await api<Forecast[]>("/forecasts/run", { method: "POST", body: JSON.stringify({ crew_member_id: selectedCrew, metric: forecastMetric }) })); } catch (error) { setMessage(String(error)); } };
  const observationCount = analysis?.facts.find((item) => item.kind === "observation_count")?.value;
  const metricSnapshots = analysis?.facts.filter((item) => item.kind === "metric_snapshot") ?? [];
  const references = new Map((analysis?.facts.filter((item) => item.kind === "reference_review") ?? []).map((item) => [String(item.metric), item]));
  const assessments = analysis?.parameter_assessments ?? [];
  const latestForecastObservation = observations.find((item) => item.metric === forecastMetric && item.value.kind === "scalar");
  const latestForecastValue = latestForecastObservation?.value.kind === "scalar" ? latestForecastObservation.value.amount : null;
  const report = analysis?.integrated_report;
  const urgentCandidate = report?.diagnostic_candidates?.find((candidate) => candidate.priority === "urgent_review");
  const complaintReview = [...(report?.complaint_review ?? [])].sort((a, b) => Date.parse(b.observed_at) - Date.parse(a.observed_at));
  const displayedComplaints = complaintReview.filter((item, index) => complaintReview.findIndex((other) => other.description === item.description) === index);
  const dataIssues = assessments.filter((item) => item.quality_status !== "unflagged" || ["invalid", "stale", "conflicting"].includes(item.status));
  const integratedFindings = (analysis?.findings ?? []).filter((item) => !["quality_flags_present", "unit_mismatch", "reference_comparison", "descriptive_series_change", "urgent_head_injury_pattern"].includes(String(item.rule_id)));
  const recommendations: (ReportItem | string)[] = report?.next_steps ?? analysis?.guidance ?? [];
  const dashboardProfile = useMemo(() => selectedProfile ? buildDashboardProfile(selectedProfile, observations, symptoms, analysis, medicalHistory) : null, [selectedProfile, observations, symptoms, analysis, medicalHistory]);
  const crewStatuses = Object.fromEntries(crew.map((member) => [member.id, statusFromAnalysis(crewAnalyses[member.id])])) as Record<string, ReturnType<typeof statusFromAnalysis>>;
  const openWorkspace = (section: "crew" | "observation" | "complaint" | "report") => { setWorkspaceTarget(section); setShowWorkspace(true); };
  useEffect(() => {
    if (!showWorkspace) return;
    const frame = requestAnimationFrame(() => document.getElementById(`workspace-${workspaceTarget}`)?.scrollIntoView({ block: "start" }));
    return () => cancelAnimationFrame(frame);
  }, [showWorkspace, workspaceTarget]);

  if (!showWorkspace) return <Dashboard profile={dashboardProfile} crew={crew} statuses={crewStatuses} observationCount={Number(report?.coverage?.observation_count ?? observationCount ?? observations.length)} symptomCount={symptoms.length} onSelectCrew={setSelectedCrew} onOpenWorkspace={openWorkspace} onRefresh={() => void runAnalysis()} message={message} />;

  return (
    <main className="workspace shell app-shell">
      <nav className="workspace-nav"><button type="button" onClick={() => setShowWorkspace(false)}>← ASTRA Summary</button><span>Input and full analysis · {selectedName}</span></nav>
      <header>
        <p className="eyebrow">LOCAL ASTRA DEMONSTRATION</p>
        <h1>ASTRA</h1>
        <p className="subtitle">Manual entry of observations for fictional profiles.</p>
        <p className="status" aria-live="polite">{message}</p>
      </header>
      <section id="workspace-crew" className="grid" aria-label="Profile and manual entry">
        <div className="card"><h2>Profile</h2><label>Select profile<select value={selectedCrew} onChange={(event) => setSelectedCrew(event.target.value)}><option value="">No profile</option>{crew.map((item) => <option key={item.id} value={item.id}>{item.display_name}</option>)}</select></label><form onSubmit={submitCrew}><label>New fictional profile<input name="name" required minLength={2} /></label><button>Create profile</button></form><h3>Profile mission</h3><form key={selectedCrew} onSubmit={submitMission}><label>Location<select name="mission_location" defaultValue={selectedProfile?.mission_location ?? "iss"}><option value="iss">ISS</option><option value="moon">Moon (fictional mission)</option><option value="mars">Mars (fictional mission)</option></select></label><label>Residential module<input name="habitat" defaultValue={selectedProfile?.habitat ?? "hermetic residential module"} required minLength={2} /></label><button disabled={!selectedCrew}>Save mission</button></form></div>
        <div id="workspace-observation" className="card"><h2>New measurement: {selectedName}</h2><form onSubmit={submitObservation}><label>Indicator<select value={metric} onChange={(event) => { const chosen = metrics.find((item) => item.id === event.target.value) ?? metrics[0]; setMetric(chosen.id); setUnit(chosen.unit); }}>{metrics.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>{metric === "blood_pressure" ? <><label>Systolic<input name="systolic" type="number" step="any" min="1" required /></label><label>Diastolic<input name="diastolic" type="number" step="any" min="1" required /></label></> : <label>Value<input name="amount" type="number" step="any" min={["spo2", "sleep_duration", "sleep_quality", "activity", "exertion_fatigue"].includes(metric) ? 0 : undefined} max={metric === "spo2" ? 100 : metric === "sleep_duration" ? 24 : ["sleep_quality", "exertion_fatigue"].includes(metric) ? 10 : undefined} required /></label>}<label>Unit<input name="unit" required value={unit} onChange={(event) => setUnit(event.target.value)} /></label><p className="muted">{metricInfo.unitHelp}</p><MeasurementContextFields metric={metric} /><button disabled={!selectedCrew}>Save measurement</button></form></div>
      </section>
      <section className="card"><h2>History: {metricInfo.label}</h2><p className="muted">Last 12 current records. Corrected and revoked versions are stored separately in the change history.</p><table><thead><tr><th>Time</th><th>Value</th><th>Origin and conditions</th><th>Actions</th></tr></thead>{visibleObservations.slice(0, 12).map((item) => <tbody key={item.id}><tr><td>{formatDate(item.observed_at)}</td><td>{item.value.kind === "blood_pressure" ? `${formatNumber(item.value.systolic)}/${formatNumber(item.value.diastolic)}` : formatNumber(item.value.amount)} {unitLabel(item.unit)}</td><td><strong>{item.synthetic ? "Synthetic" : "Manual input"}</strong><br /><small>{measurementContextText(item.measurement_context)}</small><details><summary>Record details</summary><p>Time: {formatDate(item.observed_at)}. Time zone is preserved in the original timestamp.</p><p>Baseline series: {item.measurement_context?.baseline_status ?? "unknown"}. {item.measurement_context?.subjective === true ? "Self-assessment." : item.measurement_context?.subjective === false ? "Instrument reading or count." : "Recording method is unknown."}</p>{item.measurement_context?.notes && <p>{item.measurement_context.notes}</p>}</details></td><td><button type="button" disabled={item.synthetic} onClick={() => setEditingObservation(item.id)}>Edit</button></td></tr>{editingObservation === item.id && <tr><td colSpan={4}><ObservationRevisionForm observation={item} onDone={async () => { setEditingObservation(null); invalidate(selectedCrew); await runAnalysis(); }} onCancel={() => setEditingObservation(null)} /></td></tr>}</tbody>)}</table></section>
      <section id="workspace-complaint" className="card chat-panel" aria-label="Assistant">
        <div className="chat-heading"><div><p className="eyebrow">ASTRA · LOCAL DIALOG</p><h2>Assistant · {selectedName}</h2></div><span className="chat-online">● works autonomously</span></div>
        <p className="muted">Describe the condition in plain words. The assistant will ask clarifying questions, compare the answers with the measurements of this profile, and show a data-based preliminary assessment.</p>
        {medicalHistory.length > 0 && <details><summary>Medical Card · {medicalHistory.length} episodes</summary>{[...medicalHistory].reverse().map(item => <article key={item.source_report_id}><strong>{item.status === "resolved_by_user_report" ? "Resolved by user message" : "Current Complaint"}</strong><p>Symptoms: {item.symptoms.join("; ")}</p>{item.assessment && <p>Last Assessment: {item.assessment}</p>}{item.helped.length > 0 && <p>Reported Actions: {item.helped.join("; ")}</p>}</article>)}</details>}
        <button type="button" onClick={() => void sendChatMessage("Analyze all my measurements and forecasts: what has changed, what requires attention, and why?")} disabled={!selectedCrew || chatBusy || !!profileChat.state.retry}>Analyze all indicators</button>
        {profileChat.state.error && <div role="alert">{profileChat.state.error}
          {profileChat.state.retry && <><button type="button" disabled={chatBusy} onClick={() => void profileChat.retry()}>Repeat request</button>
            <button type="button" disabled={chatBusy} onClick={profileChat.dismiss}>Continue without repetition</button></>}
        </div>}
        <div className="chat-stream" role="log" aria-live="polite">
          {chat.length === 0 && <div className="chat-empty">Start conversation: "Headache" or "What is visible by my SpO₂?"</div>}
          {chat.map((turn) => <article key={turn.id} className={`chat-bubble chat-${turn.role}`}>
            <div className="chat-meta"><strong>{turn.role === "user" ? "You" : "ASTRA"}</strong><time>{formatDate(turn.created_at)}</time>{turn.legacy && <span>archive record</span>}{turn.role === "assistant" && <span>{turn.engine?.startsWith("local_model:") ? "local AI model + knowledge base" : turn.engine?.startsWith("local_model_error:") ? "local AI assistant offline" : "local rules and knowledge base"}</span>}</div>
            <p>{turn.body}</p>
            {turn.role === "assistant" && <ChatSources citations={turn.citations ?? []} cards={scienceCards} />}
          </article>)}
          {chatBusy && <div className="chat-bubble chat-assistant">ASTRA is analyzing the message…</div>}
        </div>
        <form className="chat-compose" onSubmit={sendChat}><label className="sr-only" htmlFor="chat-message">Message to assistant</label><textarea id="chat-message" value={chatDraft} onChange={(event) => setChatDraft(event.target.value)} placeholder="Write a complaint or question…" rows={2} maxLength={2000} required disabled={!selectedCrew || chatBusy} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} /><button disabled={!selectedCrew || chatBusy || !!profileChat.state.retry || !chatDraft.trim()}>Send ↗</button></form>
      </section>
      {report?.mission_environment_context && !Array.isArray(report.mission_environment_context) && <section className="card mission-context"><h2>Environment and mission context</h2><p>{report.mission_environment_context.statement}</p>{report.mission_environment_context.sources?.map((source) => <a key={source.url} href={source.url} target="_blank" rel="noreferrer">{source.title}</a>)}</section>}
      <ResearchSources />
      <section id="workspace-report" className="card">
        <h2>Primary Measurement Review</h2>
        <p className="muted">Comparison with published adult benchmarks and personal history. Measurement conditions and applicability to space mission need to be checked separately.</p>
        <button onClick={() => void runAnalysis()} disabled={!selectedCrew}>Update Review</button>
        {analysis && <>
          {report ? <>
            <h3>Data Quality</h3>
            <p>Used {String(report.coverage?.observation_count ?? observationCount ?? 0)} measurements on {String(report.coverage?.parameter_count ?? assessments.length)} indicators.</p>
            {dataIssues.length ? <ul>{dataIssues.map((item) => <li key={item.metric}>{metricLabel(item.metric)}: {qualityText(item.quality_status)}.</li>)}</ul> : <p className="muted">No quality restrictions are declared for the latest values.</p>}
            <p className="muted">Mandatory measurement chart is not defined: recency and gaps are not clinically assessed. Educational records do not confirm accuracy for real people.</p>
            <h3>Indicator Assessment</h3>
            {assessments.length ? <table><thead><tr><th>Indicator</th><th>Last Record</th><th>Comparison and Conclusion</th></tr></thead><tbody>{assessments.map((item) => <tr key={item.metric}>
              <td><strong>{metricLabel(item.metric)}</strong><br /><small className="muted">{acquisitionText(item)} · {formatDate(item.observed_at)}</small></td>
              <td>{parameterValue(item)}</td>
              <td><strong>{assessmentStatus(item.status)}</strong><br />{item.explanation}{item.series_insight?.summary && <p className="series-insight">{item.series_insight.summary}</p>}{item.series_insight?.context_note && <p className="muted">{item.series_insight.context_note}</p>}<details><summary>How was the conclusion reached</summary><p>{personalSeriesText(item)}</p><p>{referenceAssessmentText(item)}</p><p className="muted">For clarification: {item.missing_context.map(missingContextText).join(", ")}.</p></details></td>
            </tr>)}</tbody></table> : <p className="muted">No applicable measurements available yet.</p>}
            <h3>Scenario and statistical forecast</h3>
            <p className="muted">The scenario describes conditional action alternatives. The numerical forecast below is calculated only based on the history of the selected indicator and validated against past points.</p>
            {report.condition_scenarios?.map((item) => <div className="scenario-comparison" key={item.candidate_id}><h4>{item.candidate_name}</h4><p><strong>If the following steps are performed:</strong> {item.follow}</p><p><strong>If ignored:</strong> {item.ignore}</p><p className="muted">Horizon: {item.horizon}. Individual outcome is unknown.</p><a href={item.source_url} target="_blank" rel="noreferrer">Scenario basis</a></div>)}
            {report.scenario_comparison && report.scenario_comparison.status !== "unsupported_without_evaluated_causal_model" && <div className="scenario-comparison"><p><strong>Initial event:</strong> {typeof report.scenario_comparison.initial_event === "string" ? report.scenario_comparison.initial_event : "Conditional scenario based on available data."}</p><p><strong>If the following steps are performed:</strong> {report.scenario_comparison.follow_recommendations}</p><p><strong>If not performed:</strong> {report.scenario_comparison.ignore_recommendations}</p><p className="muted">{report.scenario_comparison.uncertainty}</p>{typeof report.scenario_comparison.source_url === "string" && <a href={report.scenario_comparison.source_url} target="_blank" rel="noreferrer">{report.scenario_comparison.source_title ?? "Script source"}</a>}</div>}
            <div className="forecast-controls"><label>Indicator for statistical forecast<select value={forecastMetric} onChange={(event) => setForecastMetric(event.target.value)}>{metrics.filter((item) => item.id !== "blood_pressure").map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label><button type="button" onClick={() => void runForecast()} disabled={!selectedCrew}>Calculate 24h, 72h and 7 days</button></div>
            <ForecastCards forecasts={forecasts} parameter={forecastMetric} latestValue={latestForecastValue} />
            {readiness?.criteria_configured && <><h3>Mission readiness</h3><p><strong>{readinessStatus(readiness.status)}.</strong> {readiness.statement}</p><details><summary>Criteria and missing information</summary><ul>{readiness.contributing_factors.map((factor) => <li key={factor.criterion_id}>{factor.met ? "✓" : "—"} {factor.criterion}: {factor.evidence}</li>)}</ul><p><strong>Missing:</strong></p><ul>{readiness.missing_data.map((item, index) => <li key={index}>{item}</li>)}</ul><p className="muted">Version of internal training criteria: {readiness.criteria_version ?? "not specified"}. {readiness.criteria_scope}</p></details></>}
                    </> : <>
            <h3>What requires attention</h3>
            {analysis.findings.length === 0 ? <p>No deviations according to set rules; this does not confirm the absence of a problem.</p> : <ul>{analysis.findings.map((item, index) => <li key={index}>{findingText(item)}</li>)}</ul>}
            {analysis.hypotheses.length > 0 && <><h3>Possible explanation requiring verification</h3><ul>{analysis.hypotheses.map((item, index) => <li key={index}>{hypothesisText(item)} {typeof item.source_url === "string" && <a href={item.source_url} target="_blank" rel="noreferrer">Source</a>}</li>)}</ul></>}
            {analysis.guidance.length > 0 && <><h3>What to check</h3><ul>{analysis.guidance.map((item, index) => <li key={index}>{guidanceText(item)} {typeof item.source_url === "string" && <a href={item.source_url} target="_blank" rel="noreferrer">Source</a>}</li>)}</ul></>}
            <h3>What is unknown</h3>
            <ul>{analysis.unknowns.map((item, index) => <li key={index} className="muted">{limitationText(item)}</li>)}</ul>
          </>}
          {alerts.length > 0 && <p className="muted">Notifications in the last analysis: {alerts.length}.</p>}
        </>}
      </section>
      <section aria-label="Display limitation" className="notice">ASTRA — educational demonstration. Its results, scenarios and recommendations are not intended for independent diagnosis, treatment selection or real decision-making regarding mission clearance.</section>
    </main>
  );
}
