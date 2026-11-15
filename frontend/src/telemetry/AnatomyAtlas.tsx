import { useState, type PointerEvent } from "react";
import anatomyAtlas from "../assets/astra-anatomy-atlas.png";
import { ORGAN_BY_ID, STATE_LABELS, type CosmonautProfile, type HealthState, type OrganId } from "./dashboard-data";

type Ellipse = { cx: number; cy: number; rx: number; ry: number; rotate?: number };
type Region = { areas: Ellipse[]; dot: [number, number]; anchor: [number, number]; tip: [number, number] };

// Hotspots are aligned to the local atlas asset. They communicate only the
// selected profile's computed status; the illustration itself is static.
const REGIONS: Record<OrganId, Region> = {
  brain: {
    areas: [{ cx: 512, cy: 130, rx: 91, ry: 113 }],
    dot: [568, 92], anchor: [590, 136], tip: [687, 104],
  },
  lungs: {
    areas: [{ cx: 424, cy: 407, rx: 78, ry: 112, rotate: 12 }, { cx: 602, cy: 407, rx: 78, ry: 112, rotate: -12 }],
    dot: [377, 342], anchor: [673, 394], tip: [687, 370],
  },
  heart: {
    areas: [{ cx: 519, cy: 417, rx: 71, ry: 87, rotate: -13 }],
    dot: [569, 458], anchor: [586, 438], tip: [687, 476],
  },
  liver: {
    areas: [{ cx: 458, cy: 538, rx: 110, ry: 65, rotate: -8 }],
    dot: [384, 517], anchor: [366, 545], tip: [48, 510],
  },
  kidneys: {
    areas: [{ cx: 417, cy: 597, rx: 43, ry: 57, rotate: -12 }, { cx: 606, cy: 597, rx: 43, ry: 57, rotate: 12 }],
    dot: [628, 579], anchor: [649, 606], tip: [687, 596],
  },
  intestines: {
    areas: [{ cx: 513, cy: 670, rx: 113, ry: 96 }, { cx: 561, cy: 542, rx: 62, ry: 72, rotate: 30 }],
    dot: [568, 716], anchor: [626, 683], tip: [687, 718],
  },
};

const DRAW_ORDER: OrganId[] = ["lungs", "liver", "intestines", "kidneys", "heart", "brain"];
const TIP_W = 284;
const TIP_H = 109;

function ellipseTransform(area: Ellipse): string | undefined {
  return area.rotate ? `rotate(${area.rotate} ${area.cx} ${area.cy})` : undefined;
}

function AtlasTip({ organ, reading }: { organ: OrganId; reading: CosmonautProfile["organs"][OrganId] }) {
  const region = REGIONS[organ];
  const [x, y] = region.tip;
  const [ax, ay] = region.anchor;
  const endX = x < ax ? x + TIP_W : x;
  return <g className={`organ-tip is-visible organ--${reading.state}`} pointerEvents="none">
    <path d={`M${ax} ${ay} L${endX} ${y + TIP_H / 2}`} fill="none" stroke="rgba(148,180,220,0.55)" strokeWidth={2} />
    <rect x={x} y={y} width={TIP_W} height={TIP_H} rx={16} className="organ-tip-box" />
    <rect x={x} y={y + 15} width={5} height={TIP_H - 30} rx={2.5} className="organ-tip-accent" />
    <text x={x + 23} y={y + 34} fontSize={23} fontWeight={600} fill="var(--t-text)">{ORGAN_BY_ID[organ].name}</text>
    <text x={x + 23} y={y + 64} fontSize={17} fill="var(--t-mid)">{reading.metric.length > 25 ? `${reading.metric.slice(0, 24)}…` : reading.metric}</text>
    <text x={x + 23} y={y + 91} fontSize={16} letterSpacing={1.5} fill="var(--organ-line)">{`STATUS: ${STATE_LABELS[reading.state].toUpperCase()}`}</text>
  </g>;
}

export interface AnatomyAtlasProps {
  profile: CosmonautProfile;
  selected: OrganId;
  onSelect: (organ: OrganId) => void;
  onHoverChange: (organ: OrganId | null) => void;
}

export function AnatomyAtlas({ profile, selected, onSelect, onHoverChange }: AnatomyAtlasProps) {
  const [hoverId, setHoverId] = useState<OrganId | null>(null);
  const [focusId, setFocusId] = useState<OrganId | null>(null);
  const activeTip = hoverId ?? focusId;
  const reading = profile.organs[selected];

  const hover = (id: OrganId | null) => {
    setHoverId(id);
    onHoverChange(id);
  };

  const touch = (id: OrganId, event: PointerEvent<SVGGElement>) => {
    if (event.pointerType !== "touch") return;
    event.stopPropagation();
    hover(hoverId === id ? null : id);
  };

  return <section className="panel panel--scan flex min-h-[560px] flex-col lg:min-h-0" aria-label="Summary schematic of the astronaut's body">
    <div className="panel-h"><span className="t-label">Summary schematic of the body</span><span className={`state-chip st-${reading.state}`}>{`${ORGAN_BY_ID[selected].name} · ${STATE_LABELS[reading.state]}`}</span></div>
    <div className="min-h-0 flex-1">
      <svg viewBox="0 0 1024 1536" className="anatomy-atlas h-full max-h-[720px] w-full" role="group" aria-label="Anatomical schematic of a human. Select an area to view data." style={{ touchAction: "manipulation" }} onPointerDown={(event) => { if (event.pointerType === "touch" && hoverId !== null) hover(null); }}>
        <image href={anatomyAtlas} x={0} y={0} width={1024} height={1536} preserveAspectRatio="xMidYMid meet" pointerEvents="none" />
        <g className="atlas-ai-watermark" pointerEvents="none" aria-hidden="true">
          <rect x={712} y={1450} width={264} height={52} rx={12} />
          <text x={844} y={1483} textAnchor="middle">AI-GENERATED IMAGE</text>
        </g>
        {DRAW_ORDER.map((id) => {
          const region = REGIONS[id];
          const organ = profile.organs[id];
          const active = id === selected;
          return <g key={id} className={`atlas-region organ--${organ.state}${active ? " is-selected" : ""}`} role="button" tabIndex={0} aria-pressed={active} aria-label={`${ORGAN_BY_ID[id].name} — condition: ${STATE_LABELS[organ.state]}. ${organ.metric}. Click to open details.`} onClick={() => onSelect(id)} onPointerDown={(event) => touch(id, event)} onPointerEnter={(event) => { if (event.pointerType !== "touch") hover(id); }} onPointerLeave={(event) => { if (event.pointerType !== "touch") hover(null); }} onFocus={() => setFocusId(id)} onBlur={() => setFocusId(null)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(id); } }}>
            {region.areas.map((area, index) => <ellipse key={index} className="atlas-hit" cx={area.cx} cy={area.cy} rx={area.rx} ry={area.ry} transform={ellipseTransform(area)} />)}
            {region.areas.map((area, index) => <ellipse key={`ring-${index}`} className="atlas-highlight" cx={area.cx} cy={area.cy} rx={area.rx} ry={area.ry} transform={ellipseTransform(area)} pointerEvents="none" />)}
            <circle className="atlas-dot" cx={region.dot[0]} cy={region.dot[1]} r={8} pointerEvents="none" />
          </g>;
        })}
        {activeTip && <AtlasTip organ={activeTip} reading={profile.organs[activeTip]} />}
      </svg>
    </div>
    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-t px-3.5 py-2" style={{ borderColor: "var(--t-line)" }}>
      <div className="flex items-center gap-3.5">{(["ok", "watch", "alert", "unknown"] as HealthState[]).map((state) => <span key={state} className="flex items-center gap-1.5"><span className={`legend-dot st-${state}`} style={{ background: "var(--st)" }} /><span className="t-label" style={{ letterSpacing: "0.1em" }}>{STATE_LABELS[state]}</span></span>)}</div>
      <span className="t-hint">AI-generated illustration · select a body area to view records</span>
    </div>
  </section>;
}
