import { OBS_LEVEL_LABELS, ORGAN_BY_ID, STATE_LABELS, VITALS, type ChartSeries, type CosmonautProfile, type OrganId } from "./dashboard-data";
import { LineChart } from "./LineChart";

function VitalsPanel({ profile, hoverOrgan }: { profile: CosmonautProfile; hoverOrgan: OrganId | null }) {
  const related = hoverOrgan ? ORGAN_BY_ID[hoverOrgan].related : [];
  return <section className="panel" aria-label="Metrics summary"><div className="panel-h"><span className="t-label">Metrics summary</span><span className="num text-[10px] text-[var(--t-low)]">SAVED RECORDS</span></div><div>{VITALS.map((meta) => {
    const reading = profile.vitals[meta.id];
    return <div key={meta.id} className={`vital-row${related.includes(meta.id) ? " vital-related" : ""}`}><p className="text-[11.5px] leading-tight text-[var(--t-mid)]">{meta.name}</p><div className="flex shrink-0 items-baseline gap-1.5"><span className={`num st-${reading.state} text-[16px] font-semibold leading-none`} style={{ color: "var(--st)" }}>{reading.value}</span><span className="text-[9px] leading-none text-[var(--t-low)]">{meta.unit}</span><span className={`state-dot st-${reading.state} ml-1.5 self-center`} aria-label={STATE_LABELS[reading.state]} /></div></div>;
  })}</div></section>;
}

function OrganPanel({ profile, organId, onOpenReport }: { profile: CosmonautProfile; organId: OrganId; onOpenReport: () => void }) {
  const meta = ORGAN_BY_ID[organId];
  const reading = profile.organs[organId];
  return <section key={`${profile.id}-${organId}`} className="panel fade-key" aria-label="Card for the selected region"><div className="panel-h"><span className="t-label">Selected region</span><span className={`state-chip st-${reading.state}`}><span className="state-dot" />{STATE_LABELS[reading.state]}</span></div><div className="px-4 py-3.5"><h3 className="text-[14px] font-semibold text-[var(--t-text)]">{meta.name}</h3><p className="num mt-1 text-[11.5px] text-[var(--t-blue)]">{reading.metric}</p><p className="mt-2.5 text-[11.5px] leading-relaxed text-[var(--t-mid)]">{meta.description}</p><p className="mt-3 border-l-2 pl-3 text-[11px] leading-relaxed text-[var(--t-low)]" style={{ borderColor: "var(--t-line-strong)" }}>{reading.note}</p><p className="t-label mt-4">Related metrics</p><div className="mt-1.5 flex flex-col gap-1">{meta.related.length ? meta.related.map((id) => {
    const vital = profile.vitals[id]; const vm = VITALS.find((item) => item.id === id);
    return vm ? <div key={id} className="flex items-center justify-between gap-2 rounded-md border px-2.5 py-1.5" style={{ borderColor: "var(--t-line)" }}><span className="text-[11px] text-[var(--t-mid)]">{vm.name}</span><span className="flex items-baseline gap-1.5"><span className={`num st-${vital.state} text-[12px] font-semibold`} style={{ color: "var(--st)" }}>{vital.value}</span><span className="text-[8.5px] text-[var(--t-low)]">{vm.unit}</span><span className={`state-dot st-${vital.state} ml-0.5`} /></span></div> : null;
  }) : <p className="text-[11px] text-[var(--t-low)]">No profile measurements available.</p>}</div><button type="button" className="hud-button hud-button-subtle mt-3 w-full" onClick={onOpenReport}>Open analysis</button></div></section>;
}

function ChartCard({ profileId, chartId, title, unit, series, color, ariaLabel }: { profileId: string; chartId: string; title: string; unit: string; series: ChartSeries; color: string; ariaLabel: string }) {
  const last = series.values.at(-1);
  return <section className="panel" aria-label={title}><div className="panel-h"><span className="t-label">{title}</span><span className="num text-[10px] text-[var(--t-mid)]">{last === undefined ? "NO DATA" : `Now: ${last} ${unit}`}</span></div><div key={`${profileId}-${chartId}`} className="fade-key px-2 pb-2 pt-1">{series.values.length >= 2 ? <LineChart id={`${profileId}-${chartId}`} unit={unit} values={series.values} xTicks={series.ticks} pointLabels={series.labels} color={color} ariaLabel={ariaLabel} /> : <p className="px-3 py-6 text-[11px] text-[var(--t-low)]">For the graph, two saved records are needed.</p>}</div></section>;
}

function ObservationsPanel({ profile }: { profile: CosmonautProfile }) {
  return <section className="panel" aria-label="Medical observations"><div className="panel-h"><span className="t-label">Medical observations</span><span className="state-chip st-watch">PROFILE DATA</span></div><div>{profile.observations.length ? profile.observations.map((item) => <article key={item.id} className={`obs-item st-${item.level === "info" ? "unknown" : item.level}`}><span className="obs-mark" aria-hidden="true" /><div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-2"><span className="t-label" style={{ color: "var(--st)" }}>{`${OBS_LEVEL_LABELS[item.level]} · ${item.tag}`}</span><span className="num shrink-0 text-[9.5px] text-[var(--t-low)]">{item.time}</span></div><p className="mt-1 text-[11.5px] leading-relaxed text-[var(--t-mid)]">{item.text}</p></div></article>) : <p className="px-4 py-5 text-[11px] text-[var(--t-low)]">No records yet.</p>}</div><p className="t-hint border-t px-3.5 py-2" style={{ borderColor: "var(--t-line)" }}>Information from the selected local ASTRA profile.</p></section>;
}

export function RightColumn({ profile, organId, hoverOrgan, onOpenReport }: { profile: CosmonautProfile; organId: OrganId; hoverOrgan: OrganId | null; onOpenReport: () => void }) {
  return <div className="flex min-h-0 flex-col gap-3.5"><VitalsPanel profile={profile} hoverOrgan={hoverOrgan} /><OrganPanel profile={profile} organId={organId} onOpenReport={onOpenReport} /><ChartCard title="Pulse · saved measurements" profileId={profile.id} chartId="pulse" unit="beats per minute" series={profile.pulseSeries} color="var(--t-blue)" ariaLabel={`Graph of saved pulse measurements for ${profile.shortName}`} /><ChartCard title="SpO₂ · saved measurements" profileId={profile.id} chartId="spo2" unit="%" series={profile.spo2Series} color="var(--t-teal)" ariaLabel={`Graph of saved SpO₂ measurements for ${profile.shortName}`} /><ObservationsPanel profile={profile} /></div>;
}
