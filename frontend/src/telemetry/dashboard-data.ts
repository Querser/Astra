import type { Analysis, CrewMember, Observation as StoredObservation, SymptomReport } from "../api";

export type OrganId = "brain" | "heart" | "lungs" | "liver" | "kidneys" | "intestines";
export type HealthState = "ok" | "watch" | "alert" | "unknown";
export type VitalId = "pulse" | "spo2" | "temp" | "bp" | "sleep" | "activity";
export type ObservationLevel = "info" | "watch" | "alert";
export type MedicalEpisode = { source_report_id: string; topic: string; symptoms: string[]; assessment: string; helped: string[]; status: string; citations?: string[] };

export interface OrganMeta {
  id: OrganId;
  name: string;
  description: string;
  related: VitalId[];
}

export interface VitalMeta {
  id: VitalId;
  name: string;
  metric: string;
  unit: string;
}

export interface VitalReading {
  value: string;
  state: HealthState;
}

export interface OrganReading {
  state: HealthState;
  metric: string;
  note: string;
}

export interface DashboardObservation {
  id: string;
  time: string;
  level: ObservationLevel;
  tag: string;
  text: string;
}

export interface ChartSeries {
  values: number[];
  labels: string[];
  ticks: { index: number; label: string }[];
}

export interface CosmonautProfile {
  id: string;
  shortName: string;
  fullName: string;
  role: string;
  location: string;
  status: HealthState;
  statusNote: string;
  hue: number;
  vitals: Record<VitalId, VitalReading>;
  organs: Record<OrganId, OrganReading>;
  observations: DashboardObservation[];
  pulseSeries: ChartSeries;
  spo2Series: ChartSeries;
}

export const STATE_LABELS: Record<HealthState, string> = {
  ok: "Norm",
  watch: "Observation",
  alert: "Attention",
  unknown: "No data",
};

export const OBS_LEVEL_LABELS: Record<ObservationLevel, string> = {
  info: "Record",
  watch: "Observation",
  alert: "Attention",
};

export const ORGANS: OrganMeta[] = [
  { id: "brain", name: "Head and Sleep", description: "Complaints after head trauma and preserved sleep indicators.", related: ["sleep", "pulse"] },
  { id: "heart", name: "Heart and Vessels", description: "Latest pulse and blood pressure records.", related: ["pulse", "bp"] },
  { id: "lungs", name: "Breathing", description: "Latest SpO₂ records and complaints related to breathing.", related: ["spo2", "activity"] },
  { id: "liver", name: "Liver", description: "In the current set ASTRA there is no separate assessment of liver function.", related: [] },
  { id: "kidneys", name: "Kidneys", description: "In the current set ASTRA there is no separate assessment of kidney function.", related: [] },
  { id: "intestines", name: "Digestion", description: "There is no separate assessment of digestion in the current ASTRA set.", related: [] },
];

export const ORGAN_BY_ID = Object.fromEntries(ORGANS.map((organ) => [organ.id, organ])) as Record<OrganId, OrganMeta>;

export const VITALS: VitalMeta[] = [
  { id: "pulse", name: "Pulse", metric: "heart_rate", unit: "beats per minute" },
  { id: "spo2", name: "SpO₂", metric: "spo2", unit: "%" },
  { id: "temp", name: "Temperature", metric: "body_temperature", unit: "°C" },
  { id: "bp", name: "Blood Pressure", metric: "blood_pressure", unit: "mm Hg" },
  { id: "sleep", name: "Sleep", metric: "sleep_duration", unit: "h" },
  { id: "activity", name: "Activity", metric: "activity", unit: "steps" },
];

const OTHER_METRICS: Record<string, { name: string; unit: string }> = {
  respiratory_rate: { name: "Respiratory Rate", unit: "breaths/min" },
  sleep_quality: { name: "Sleep Self-Assessment", unit: "points" },
  exertion_fatigue: { name: "Fatigue", unit: "points" },
};

const STATE_RANK: Record<HealthState, number> = { unknown: -1, ok: 0, watch: 1, alert: 2 };
const missionName: Record<NonNullable<CrewMember["mission_location"]>, string> = {
  iss: "ISS · orbital segment",
  moon: "Moon · training base",
  mars: "Mars · training base",
};

function timeLabel(iso: string | null | undefined): string {
  if (!iso) return "time not specified";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "time not specified";
  return new Intl.DateTimeFormat("en-US", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}

function shortName(value: string): string {
  const withoutBrand = value.replace(/^ASTRA\s*[—-]\s*/i, "");
  return withoutBrand.length > 32 ? `${withoutBrand.slice(0, 29)}…` : withoutBrand;
}

export function hueForId(id: string): number {
  let sum = 0;
  for (const character of id) sum = (sum * 31 + character.charCodeAt(0)) % 43;
  return 178 + sum;
}

function numericValue(item: StoredObservation): string {
  if (item.value.kind === "blood_pressure") return `${item.value.systolic}/${item.value.diastolic}`;
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }).format(item.value.amount);
}

function displayUnit(item: StoredObservation, defaultUnit: string): string {
  if (item.unit !== "score" || item.value.kind !== "scalar" || !Number.isInteger(item.value.amount)) return defaultUnit;
  const amount = Math.abs(item.value.amount);
  const lastTwo = amount % 100;
  if (lastTwo >= 11 && lastTwo <= 14) return "points";
  if (amount % 10 === 1) return "point";
  if (amount % 10 >= 2 && amount % 10 <= 4) return "points";
  return "points";
}

function sortedByTime(items: StoredObservation[]): StoredObservation[] {
  return [...items].sort((a, b) => Date.parse(a.observed_at) - Date.parse(b.observed_at));
}

function stateForMetric(metric: string, analysis: Analysis | null): HealthState {
  const assessment = analysis?.parameter_assessments?.find((item) => item.metric === metric);
  if (!assessment) return "unknown";
  const candidate = analysis?.integrated_report?.diagnostic_candidates?.find((item) => item.primary_metric === metric);
  if (candidate?.priority === "urgent_review" || candidate?.id === "D.POSSIBLE_HYPOXEMIA") return "alert";
  if (candidate || assessment.status === "outside_available_reference") return "watch";
  if (assessment.status === "within_available_reference") return "ok";
  return "unknown";
}

export function statusFromAnalysis(analysis: Analysis | null | undefined): HealthState {
  if (!analysis) return "unknown";
  const candidates = analysis.integrated_report?.diagnostic_candidates ?? [];
  if (candidates.some((item) => item.priority === "urgent_review" || item.id === "D.POSSIBLE_HYPOXEMIA")) return "alert";
  if (candidates.length || analysis.parameter_assessments?.some((item) => item.status === "outside_available_reference")) return "watch";
  if (analysis.parameter_assessments?.some((item) => item.status === "within_available_reference")) return "ok";
  return "unknown";
}

function chartSeries(observations: StoredObservation[], metric: string, limit: number): ChartSeries {
  const items = sortedByTime(observations.filter((item) => item.metric === metric && item.value.kind === "scalar")).slice(-limit);
  const values = items.map((item) => item.value.kind === "scalar" ? item.value.amount : 0);
  const labels = items.map((item) => timeLabel(item.observed_at));
  const tickIndexes = values.length < 2 ? [] : [...new Set([0, Math.floor((values.length - 1) / 2), values.length - 1])];
  return { values, labels, ticks: tickIndexes.map((index) => ({ index, label: labels[index] })) };
}

export function buildDashboardProfile(
  member: CrewMember,
  observations: StoredObservation[],
  symptoms: SymptomReport[],
  analysis: Analysis | null,
  medicalHistory: MedicalEpisode[] = [],
): CosmonautProfile {
  const ordered = sortedByTime(observations);
  const latest = new Map<string, StoredObservation>();
  for (const item of ordered) latest.set(item.metric, item);
  const vitals = Object.fromEntries(VITALS.map((meta) => {
    const item = latest.get(meta.metric);
    return [meta.id, { value: item ? numericValue(item) : "—", state: item ? stateForMetric(meta.metric, analysis) : "unknown" }];
  })) as Record<VitalId, VitalReading>;
  const candidates = analysis?.integrated_report?.diagnostic_candidates ?? [];
  const head = candidates.find((item) => item.id === "D.POSSIBLE_HEAD_INJURY");
  const sleep = candidates.find((item) => item.id === "D.SLEEP_DEFICIENCY_PATTERN");
  const heart = candidates.find((item) => item.id === "D.POSSIBLE_HYPERTENSION");
  const lungs = candidates.find((item) => item.id === "D.POSSIBLE_HYPOXEMIA");
  const latestEpisode = (topics: string[]) => [...medicalHistory].reverse().find(item => topics.includes(item.topic));
  const activeHead = latestEpisode(["headache", "head", "fever_headache"]);
  const heartEpisode = latestEpisode(["blood_pressure", "chest_pain"]);
  const lungEpisode = latestEpisode(["oxygen"]);
  const digestiveEpisode = latestEpisode(["food"]);
  const episodeState = (episode: MedicalEpisode | undefined, fallback: HealthState): HealthState =>
    episode?.status === "active" ? "alert" : episode?.status === "resolved_by_user_report" ? "ok" : fallback;
  const brainState: HealthState = episodeState(activeHead, head ? "alert" : sleep ? "watch" : vitals.sleep.state);
  const heartState: HealthState = heart ? "watch" : STATE_RANK[vitals.pulse.state] >= STATE_RANK[vitals.bp.state] ? vitals.pulse.state : vitals.bp.state;
  const lungState: HealthState = lungs ? "alert" : vitals.spo2.state;
  const organs: Record<OrganId, OrganReading> = {
    brain: { state: brainState, metric: activeHead?.status === "active" ? "Current complaint about head" : activeHead?.status === "resolved_by_user_report" ? "Symptom resolved by report" : head?.name ?? (vitals.sleep.value !== "—" ? `Sleep ${vitals.sleep.value} ch` : "No related records"), note: activeHead?.assessment ?? head?.evidence ?? sleep?.evidence ?? "Assessment is limited to saved complaints and sleep records; cognitive test was not performed." },
    heart: { state: episodeState(heartEpisode, heartState), metric: heartEpisode?.status === "active" ? "Current Complaint" : `Pulse ${vitals.pulse.value} · BP ${vitals.bp.value}`, note: heartEpisode?.assessment ?? heart?.evidence ?? "Only related measurements are shown; ECG and contractility assessment were not performed." },
    lungs: { state: episodeState(lungEpisode, lungState), metric: lungEpisode?.status === "active" ? "Current Complaint" : `SpO₂ ${vitals.spo2.value} %`, note: lungEpisode?.assessment ?? lungs?.evidence ?? "Displayed saturation from saved records; the reason for changes to it is not determined." },
    liver: { state: "unknown", metric: "No profile data", note: "Biochemical data and liver function in active analysis are not evaluated." },
    kidneys: { state: "unknown", metric: "No profile data", note: "Kidney function data in active analysis are not evaluated." },
    intestines: { state: episodeState(digestiveEpisode, "unknown"), metric: digestiveEpisode?.status === "active" ? "Current complaint about digestion" : digestiveEpisode?.status === "resolved_by_user_report" ? "Symptom resolved by report" : "No profile data", note: digestiveEpisode?.assessment ?? "Digestion data in active analysis are not evaluated." },
  };
  const feed: DashboardObservation[] = candidates.map((item) => ({
    id: `candidate-${item.id}`, time: timeLabel(analysis?.created_at),
    level: item.priority === "urgent_review" || item.id === "D.POSSIBLE_HYPOXEMIA" ? "alert" : "watch",
    tag: "ANALYSIS", text: `${item.name}: ${item.evidence}`,
  }));
  for (const symptom of [...symptoms].sort((a, b) => Date.parse(b.observed_at) - Date.parse(a.observed_at)).slice(0, 2)) {
    feed.push({ id: symptom.id, time: timeLabel(symptom.observed_at), level: "info", tag: "COMPLAINT", text: symptom.description });
  }
  for (const item of ordered.slice(-5).reverse()) {
    if (feed.length >= 5) break;
    const meta = VITALS.find((vital) => vital.metric === item.metric) ?? OTHER_METRICS[item.metric];
    feed.push({ id: item.id, time: timeLabel(item.observed_at), level: "info", tag: "MEASUREMENT", text: `${meta?.name ?? item.metric}: ${numericValue(item)} ${displayUnit(item, meta?.unit ?? item.unit)}${item.synthetic ? " · study record" : ""}.` });
  }
  const status = statusFromAnalysis(analysis);
  return {
    id: member.id,
    shortName: shortName(member.display_name),
    fullName: member.display_name,
    role: "Crew profile",
    location: member.mission_location ? missionName[member.mission_location] : "Mission not specified",
    status,
    statusNote: candidates[0]?.name ?? (status === "ok" ? "No deviations detected based on available metrics" : "Evaluation is built based on saved records"),
    hue: hueForId(member.id),
    vitals,
    organs,
    observations: feed,
    pulseSeries: chartSeries(observations, "heart_rate", 24),
    spo2Series: chartSeries(observations, "spo2", 14),
  };
}
