import type { CosmonautProfile } from "./dashboard-data";
import { STATE_LABELS } from "./dashboard-data";

function AstraMark() {
  return (
    <svg viewBox="0 0 36 36" width={34} height={34} aria-hidden="true" focusable="false">
      <path d="M18 2.5 L31.5 10.25 V25.75 L18 33.5 L4.5 25.75 V10.25 Z" fill="none" stroke="rgba(77,157,255,0.5)" strokeWidth={1.3} />
      <path d="M18 7.5 L27.2 12.75 V23.25 L18 28.5 L8.8 23.25 V12.75 Z" fill="rgba(77,157,255,0.08)" stroke="rgba(126,166,224,0.22)" />
      <path d="M10.5 18 H14.4 L16.2 13.8 L18.6 22 L20.4 18 H25.5" fill="none" stroke="#4d9dff" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={18} cy={18} r={1.5} fill="#38c8b4" />
    </svg>
  );
}

export function TopBar({ profile, onOpenWorkspace, onRefresh }: {
  profile: CosmonautProfile;
  onOpenWorkspace: () => void;
  onRefresh: () => void;
}) {
  return (
    <header className="telemetry-top sticky top-0 z-20 border-b backdrop-blur-md" style={{ borderColor: "var(--t-line)", background: "rgba(4, 7, 13, 0.9)" }}>
      <div className="mx-auto flex w-full max-w-[1760px] flex-wrap items-center gap-x-5 gap-y-2.5 px-4 py-2.5">
        <div className="rise-in flex items-center gap-3">
          <AstraMark />
          <div>
            <p className="text-[15px] font-bold leading-none tracking-[0.22em] text-[var(--t-text)]">ASTRA</p>
            <p className="t-label mt-1.5">Local crew health analysis</p>
          </div>
          <span className="state-chip st-watch ml-1.5">Educational prototype</span>
        </div>
        <div className="divider-v hidden h-9 md:block" />
        <div className="hidden min-w-0 md:block">
          <span className="t-label">Mission · selected profile</span>
          <p className="mt-1 max-w-[260px] truncate text-[12px] text-[var(--t-mid)]">{profile.location}</p>
        </div>
        <div className="ml-auto flex items-center gap-2.5">
          <span className={`state-chip st-${profile.status}`}><span className="state-dot" />{STATE_LABELS[profile.status]}</span>
          <button type="button" className="hud-button hud-button-subtle" onClick={onRefresh}>Update</button>
          <button type="button" className="hud-button" onClick={onOpenWorkspace}>Input and Analysis</button>
        </div>
      </div>
    </header>
  );
}
