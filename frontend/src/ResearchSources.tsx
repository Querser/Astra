import { useEffect, useMemo, useState } from "react";
import { api } from "./api";

type RadiationPoint = { timestamp: string; absorbed_dose_rate: number | null; dose_equivalent_rate: number | null };
type RadLab = { dataset_id: string; version: string; source_url: string; retrieved_at: string; instrument_id: string; location: string; unit: { absorbed_dose_rate: string; dose_equivalent_rate: string }; points: RadiationPoint[]; sampling_seconds?: { minimum: number; median: number; maximum: number }; missing_equivalent_count?: number };
type LabRow = { participant_id: string; analyte: string; value: number | null; unit: string | null; timepoint: string; reference_low: number | null; reference_high: number | null; missing: boolean };
type LabData = { dataset_id: string; version: string; file?: string; source_url: string; retrieved_at: string; specimen?: string; assay?: string; reference_context?: string; participants: string[]; observations: LabRow[] };
export type ScienceCard = { id: string; title_ru?: string; title?: string; topic?: string; summary_ru?: string; summary?: string; supported_interpretation?: string; source_organization?: string; source_title?: string; original_document_title?: string; source_url?: string; section?: string | null; revision?: string | null; retrieved_at?: string; limitations_ru?: string; limitations?: string; source?: { organization: string; title: string; url: string; version?: string | null; section?: string | null } };

function SourceLink({ url, label = "Open original ↗" }: { url?: string; label?: string }) {
  return url ? <a href={url} target="_blank" rel="noreferrer">{label}</a> : <span>Source address not specified</span>;
}

function RadiationSeries({ data }: { data: RadLab }) {
  const equivalentAvailable = data.points.some(point => typeof point.dose_equivalent_rate === "number");
  const values = data.points.map(point => equivalentAvailable ? point.dose_equivalent_rate : point.absorbed_dose_rate).filter((value): value is number => typeof value === "number");
  const lo = Math.min(...values), hi = Math.max(...values);
  const line = values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${90 - ((value - lo) / Math.max(hi - lo, 0.001)) * 80}`).join(" ");
  return <>
    <p>Archived environmental measurements from instrument <strong>{data.instrument_id}</strong> · {data.location}. This series is not a personal radiation dose for any crew member.</p>
    {values.length > 1 && <svg className="research-series" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={`Historical series of dose rate ${equivalentAvailable ? "equivalent" : "absorbed"} dose`}><polyline points={line} fill="none" stroke="currentColor" strokeWidth="1.4" vectorEffect="non-scaling-stroke" /></svg>}
    {values.length > 0 && <p>Displayed {equivalentAvailable ? "equivalent" : "absorbed"} dose rate: {Math.min(...values).toFixed(3)}–{Math.max(...values).toFixed(3)} {equivalentAvailable ? data.unit.dose_equivalent_rate : data.unit.absorbed_dose_rate}.</p>}
    {!equivalentAvailable && <p className="muted">For this device and time interval, equivalent dose rate in the export is not available.</p>}
    <div className="research-summary"><span>Points: {data.points.length}</span><span>Start: {data.points[0]?.timestamp ?? "—"}</span><span>End: {data.points.at(-1)?.timestamp ?? "—"}</span></div>
    <p className="muted">In the original file, the time zone of the time stamps is not specified; time is shown without conversion.</p>
    <details><summary>Units and Origin</summary><p>Absorbed dose rate: {data.unit.absorbed_dose_rate}; equivalent dose rate: {data.unit.dose_equivalent_rate}. The quantities are not interchangeable.</p>{data.sampling_seconds && <p>Actual interval between points: median {data.sampling_seconds.median} s (range {data.sampling_seconds.minimum}–{data.sampling_seconds.maximum} s).</p>}<p>{data.dataset_id} · version {data.version} · received {data.retrieved_at}. <SourceLink url={data.source_url} label="Source: NASA RadLab ↗" /></p></details>
  </>;
}

function LabSeries({ data }: { data: LabData }) {
  const [participant, setParticipant] = useState("");
  const [analyte, setAnalyte] = useState("");
  const participants = data.participants ?? [];
  const selectedParticipant = participants.includes(participant) ? participant : participants[0] ?? "";
  const analytes = useMemo(() => [...new Set(data.observations.filter(row => row.participant_id === selectedParticipant).map(row => row.analyte))].sort(), [data.observations, selectedParticipant]);
  const selectedAnalyte = analytes.includes(analyte) ? analyte : analytes[0] ?? "";
  const rows = data.observations.filter(row => row.participant_id === selectedParticipant && row.analyte === selectedAnalyte);
  return <>
    <p>Four anonymous participants of a public study. Samples before and after a short mission; this is a separate set, not the data of the selected ASTRA profile.</p>
    <div className="research-controls"><label>Participant<select value={selectedParticipant} onChange={event => { setParticipant(event.target.value); setAnalyte(""); }}>{participants.map(id => <option key={id} value={id}>{id}</option>)}</select></label><label>Analyte<select value={selectedAnalyte} onChange={event => setAnalyte(event.target.value)}>{analytes.map(name => <option key={name} value={name}>{name}</option>)}</select></label></div>
    <div className="research-scroll"><table><thead><tr><th>Relative to mission</th><th>Result</th><th>Lab Limits</th></tr></thead><tbody>{rows.map((row, index) => <tr key={`${row.participant_id}-${row.analyte}-${row.timepoint}-${index}`}><td>{row.timepoint}</td><td>{row.missing ? "No value" : `${row.value} ${row.unit ?? ""}`}</td><td>{row.reference_low == null || row.reference_high == null ? "Not specified" : `${row.reference_low}–${row.reference_high} ${row.unit ?? ""}`}</td></tr>)}</tbody></table></div>
    <details><summary>Source and comparison limits</summary><p>{data.dataset_id} · version {data.version} · received {data.retrieved_at}. File: {data.file ?? "not specified"}; sample: {data.specimen ?? "not specified"}; analysis: {data.assay ?? "not specified"}.</p><p>{data.reference_context ?? "Laboratory limits are saved in the context of the original analysis and do not become a norm for the ASTRA crew."} <SourceLink url={data.source_url} label="Source: NASA OSDR ↗" /></p></details>
  </>;
}

export function ResearchSources() {
  const [cards, setCards] = useState<ScienceCard[]>([]);
  const [radlab, setRadlab] = useState<RadLab | null>(null);
  const [lab, setLab] = useState<LabData | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  useEffect(() => {
    let active = true;
    void Promise.allSettled([api<ScienceCard[] | { cards: ScienceCard[] }>("/reference/space-science"), api<RadLab>("/research/radlab"), api<LabData>("/research/osd-575")]).then(results => {
      if (!active) return;
      if (results[0].status === "fulfilled") setCards(Array.isArray(results[0].value) ? results[0].value : results[0].value.cards);
      if (results[1].status === "fulfilled") setRadlab(results[1].value);
      if (results[2].status === "fulfilled") setLab(results[2].value);
      setErrors(results.flatMap((result, index) => result.status === "rejected" ? [`${["Reference", "RadLab", "OSD-575"][index]}: local data unavailable.`] : []));
    });
    return () => { active = false; };
  }, []);
  return <section id="workspace-research" className="research-sources" aria-label="Scientific and archival data">
    <div className="card"><p className="eyebrow">DATA SOURCES</p><h2>Scientific and archival data</h2><p className="muted">Local copies of studies and archival measurements. They are separated from the manual crew history and are available without network connection.</p>{errors.map(error => <p className="muted" key={error}>{error}</p>)}</div>
    <div className="research-grid"><article className="card"><h3>Radiation · RadLab archive</h3>{radlab ? <RadiationSeries data={radlab} /> : <p className="muted">Loading local archive…</p>}</article><article className="card"><h3>Laboratory data · OSD-575</h3>{lab ? <LabSeries data={lab} /> : <p className="muted">Loading local study…</p>}</article></div>
    <div className="card"><h3>Space Health · local reference</h3><p className="muted">Brief materials from official sources with sections and limitations. The assistant selects relevant card(s) related to the question.</p><div className="science-card-grid">{cards.map(card => { const sourceLabel = [card.source?.organization ?? card.source_organization, card.source?.title ?? card.source_title ?? card.original_document_title, card.source?.section ?? card.section, card.source?.version ?? card.revision].filter(Boolean).join(" · "); return <details key={card.id} className="science-card"><summary>{card.title_ru ?? card.title ?? card.topic ?? card.id}</summary><p>{card.summary_ru ?? card.supported_interpretation ?? card.summary ?? "Description is in the local card."}</p><p className="muted">{card.limitations_ru ?? card.limitations}</p><p className="muted">{card.retrieved_at ? `Received ${card.retrieved_at}. ` : ""}<SourceLink url={card.source?.url ?? card.source_url} label={`${sourceLabel || "Original source"} ↗`} /></p></details>; })}</div></div>
  </section>;
}
