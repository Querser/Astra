import { useState } from "react";
import type { CrewMember } from "../api";
import { AnatomyAtlas } from "./AnatomyAtlas";
import { CrewColumn } from "./CrewColumn";
import { RightColumn } from "./RightColumn";
import { TopBar } from "./TopBar";
import type { CosmonautProfile, HealthState, OrganId } from "./dashboard-data";

const organPriority: OrganId[] = ["brain", "lungs", "heart", "liver", "kidneys", "intestines"];
const statePriority: Record<HealthState, number> = { alert: 3, watch: 2, ok: 1, unknown: 0 };

function initialOrgan(profile: CosmonautProfile): OrganId {
  return organPriority.reduce<OrganId>((selected, current) =>
    statePriority[profile.organs[current].state] > statePriority[profile.organs[selected].state] ? current : selected, "heart");
}

export function Dashboard({ profile, crew, statuses, observationCount, symptomCount, onSelectCrew, onOpenWorkspace, onRefresh, message }: {
  profile: CosmonautProfile | null;
  crew: CrewMember[];
  statuses: Record<string, HealthState>;
  observationCount: number;
  symptomCount: number;
  onSelectCrew: (id: string) => void;
  onOpenWorkspace: (section: "crew" | "observation" | "complaint" | "report") => void;
  onRefresh: () => void;
  message: string;
}) {
  const [selection, setSelection] = useState<{ profileId: string; organId: OrganId } | null>(null);
  const [hoverOrgan, setHoverOrgan] = useState<OrganId | null>(null);
  if (!profile) return <div className="telemetry min-h-screen"><header className="p-5 text-lg font-bold tracking-[0.2em]">ASTRA</header><main className="panel mx-auto max-w-xl p-6"><h1 className="text-xl font-semibold">No profile selected</h1><p className="mt-2 text-[var(--t-mid)]">{message}</p><button type="button" className="hud-button mt-4" onClick={() => onOpenWorkspace("crew")}>Create or select a profile</button></main></div>;
  const organId = selection?.profileId === profile.id ? selection.organId : initialOrgan(profile);
  return <div className="telemetry flex min-h-screen flex-col lg:h-screen lg:overflow-hidden"><TopBar profile={profile} onOpenWorkspace={() => onOpenWorkspace("report")} onRefresh={onRefresh} /><main className="mx-auto grid w-full max-w-[1760px] flex-1 grid-cols-1 gap-3.5 p-3.5 lg:min-h-0 lg:grid-cols-[300px_minmax(0,1fr)_348px] lg:overflow-hidden"><div className="col-scroll rise-in lg:min-h-0 lg:overflow-y-auto lg:pr-1"><CrewColumn profile={profile} crew={crew} statuses={statuses} observationCount={observationCount} symptomCount={symptomCount} onSelect={onSelectCrew} onOpenWorkspace={onOpenWorkspace} /></div><div className="col-scroll rise-in lg:min-h-0 lg:overflow-hidden [&>section]:h-full" style={{ animationDelay: "90ms" }}><AnatomyAtlas profile={profile} selected={organId} onSelect={(nextOrganId) => setSelection({ profileId: profile.id, organId: nextOrganId })} onHoverChange={setHoverOrgan} /></div><div className="col-scroll rise-in lg:min-h-0 lg:overflow-y-auto lg:pl-1" style={{ animationDelay: "180ms" }}><RightColumn profile={profile} organId={organId} hoverOrgan={hoverOrgan} onOpenReport={() => onOpenWorkspace("report")} /></div></main></div>;
}
