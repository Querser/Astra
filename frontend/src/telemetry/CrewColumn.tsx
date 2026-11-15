import { useId } from "react";
import type { CrewMember } from "../api";
import { hueForId, STATE_LABELS, type CosmonautProfile, type HealthState } from "./dashboard-data";

export function CrewAvatar({ hue, size = 84, className }: { hue: number; size?: number; className?: string }) {
  const accent = `hsl(${hue} 65% 60%)`;
  const accentDim = `hsl(${hue} 45% 32%)`;
  const gid = `av-grad-${useId().replace(/:/g, "")}`;
  return (
    <svg viewBox="0 0 84 84" width={size} height={size} className={className} aria-hidden="true" focusable="false">
      <defs><linearGradient id={gid} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#141f38" /><stop offset="1" stopColor="#0a1120" /></linearGradient></defs>
      <circle cx={42} cy={42} r={40} fill={`url(#${gid})`} stroke="rgba(126,166,224,0.28)" />
      <circle cx={42} cy={42} r={34} fill="none" stroke={accentDim} strokeOpacity={0.5} />
      <circle cx={42} cy={39} r={21} fill="#101a30" stroke="rgba(148,180,220,0.35)" />
      <path d="M21.4 37 A21 21 0 0 0 62.6 37 Z" fill="#060b15" stroke={accentDim} strokeOpacity={0.9} />
      <path d="M29 50 L43 32" stroke={accent} strokeOpacity={0.35} strokeWidth={2.5} strokeLinecap="round" />
      <circle cx={42} cy={13} r={2.2} fill={accent} />
      <rect x={31} y={59} width={22} height={7} rx={3.5} fill="none" stroke="rgba(148,180,220,0.35)" />
    </svg>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return <div className="flex items-baseline justify-between gap-2 border-b border-dashed border-[rgba(126,166,224,0.12)] pb-1.5 last:border-none last:pb-0"><span className="t-label">{label}</span><span className="num text-right text-[11px] text-[var(--t-mid)]">{value}</span></div>;
}

export function CrewColumn({ profile, crew, statuses, observationCount, symptomCount, onSelect, onOpenWorkspace }: {
  profile: CosmonautProfile;
  crew: CrewMember[];
  statuses: Record<string, HealthState>;
  observationCount: number;
  symptomCount: number;
  onSelect: (id: string) => void;
  onOpenWorkspace: (section: "crew" | "observation" | "complaint" | "report") => void;
}) {
  return (
    <div className="flex min-h-0 flex-col gap-3.5">
      <section className="panel p-4" aria-label="Astronaut card">
        <p className="t-label mb-3">Selected profile</p>
        <div className="flex items-center gap-3.5"><CrewAvatar hue={profile.hue} className="shrink-0" /><div className="min-w-0"><p className="truncate text-[15px] font-semibold leading-tight text-[var(--t-text)]">{profile.fullName}</p><p className="mt-0.5 text-[11px] uppercase tracking-[0.14em] text-[var(--t-low)]">{profile.role}</p><p className={`state-chip st-${profile.status} mt-2.5`}><span className="state-dot" />{STATE_LABELS[profile.status]}</p></div></div>
        <p className="mt-3 text-[11px] leading-relaxed text-[var(--t-mid)]">{profile.statusNote}</p>
        <div className="mt-3 flex flex-col gap-1.5"><MetaRow label="Location" value={profile.location} /><MetaRow label="Measurements" value={String(observationCount)} /><MetaRow label="Complaints" value={String(symptomCount)} /></div>
      </section>

      <section className="panel" aria-label="Selection of crew member">
        <div className="panel-h"><span className="t-label">Crew · profiles</span><span className="num text-[10px] text-[var(--t-low)]">{crew.length}</span></div>
        <div className="flex flex-col gap-1 p-2">{crew.map((member) => {
          const status = statuses[member.id] ?? "unknown";
          return <button key={member.id} type="button" className="crew-item" aria-pressed={member.id === profile.id} onClick={() => onSelect(member.id)}><CrewAvatar hue={hueForId(member.id)} size={30} className="shrink-0" /><span className="min-w-0 flex-1"><span className="block truncate text-[12px] font-medium leading-tight">{member.display_name.replace(/^ASTRA\s*[—-]\s*/i, "")}</span><span className="block truncate text-[10px] leading-tight text-[var(--t-low)]">{member.mission_location?.toUpperCase() ?? "MISSION NOT SPECIFIED"}</span></span><span className={`state-dot st-${status}`} aria-label={STATE_LABELS[status]} /></button>;
        })}</div>
        <p className="t-hint border-t px-3 py-2" style={{ borderColor: "var(--t-line)" }}>Selecting a profile updates measurements, diagram and analysis.</p>
      </section>

      <section className="panel" aria-label="Profile Actions">
        <div className="panel-h"><span className="t-label">Actions</span><span className="num text-[10px] text-[var(--t-teal)]">LOCAL</span></div>
        <div className="flex flex-col gap-2 p-3"><button type="button" className="hud-button" onClick={() => onOpenWorkspace("complaint")}>Add Complaint</button><button type="button" className="hud-button hud-button-subtle" onClick={() => onOpenWorkspace("observation")}>Enter Measurement</button><button type="button" className="hud-button hud-button-subtle" onClick={() => onOpenWorkspace("report")}>Full Report and Forecast</button><button type="button" className="hud-button hud-button-subtle" onClick={() => onOpenWorkspace("crew")}>Profiles and Mission</button></div>
      </section>
    </div>
  );
}
