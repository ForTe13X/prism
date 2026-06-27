import { useEffect, useMemo, useState } from "react";
import { fetchNexusView } from "./api";
import type { NexusView as NexusViewData, NexusUnit } from "./types";

// The two domains live at fixed columns; each bulges toward the centre so the gap between them is the
// "collision zone" where verified bridges light. Cold cyan = INFRA, warm amber = LIBRARY (the only
// hard-coded colours — they encode the two domains, nothing else).
const W = 920;
const H = 600;
const COLD = "#39a7c8";
const WARM = "#d29240";
const SEEDS = Array.from({ length: 8 }, (_, i) => `xe-${i}`);

function pos(idx: number, n: number, side: "A" | "B") {
  const t = n > 1 ? idx / (n - 1) : 0.5;
  const y = 70 + t * (H - 140);
  const bulge = 56 * Math.sin(t * Math.PI);
  const x = side === "A" ? 250 + bulge : W - 250 - bulge;
  return { x, y };
}

export default function NexusView() {
  const [seed, setSeed] = useState(SEEDS[0]);
  const [data, setData] = useState<NexusViewData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError("");
    fetchNexusView(seed)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [seed]);

  const layout = useMemo(() => {
    if (!data) return null;
    const aPos = new Map<number, { x: number; y: number }>();
    const bPos = new Map<number, { x: number; y: number }>();
    data.A.units.forEach((u: NexusUnit) => aPos.set(u.idx, pos(u.idx, data.A.units.length, "A")));
    data.B.units.forEach((u: NexusUnit) => bPos.set(u.idx, pos(u.idx, data.B.units.length, "B")));
    // draw ghosts first (behind), then medium, then the glowing high bridges on top
    const order = { coincidence: 0, medium: 1, high: 2 } as const;
    const bridges = [...data.bridges].sort((p, q) => order[p.confidence] - order[q.confidence]);
    return { aPos, bPos, bridges };
  }, [data]);

  const sc = data?.scorecard;

  return (
    <div className="pr-nexus">
      <div className="pr-nexus-bar">
        <span className="pr-nexus-title">星系碰撞 · 跨域 nexus（INFRA × LIBRARY）</span>
        <label className="pr-nexus-seed">
          种子
          <select value={seed} onChange={(e) => setSeed(e.target.value)}>
            {SEEDS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="pr-error">加载失败:{error}</p>}
      {!data && !error && <p className="pr-muted">加载中…</p>}

      {data && layout && (
        <div className="pr-nexus-stage">
          <svg viewBox={`0 0 ${W} ${H}`} className="pr-nexus-svg" role="img" aria-label="跨域 nexus 碰撞视图">
            <defs>
              <filter id="nexglow" x="-60%" y="-60%" width="220%" height="220%">
                <feGaussianBlur stdDeviation="3.4" result="b" />
                <feMerge>
                  <feMergeNode in="b" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <rect x={0} y={0} width={W} height={H} className="pr-nexus-bg" />
            {/* candidate bridges */}
            {layout.bridges.map((br, i) => {
              const a = layout.aPos.get(br.a_idx);
              const b = layout.bPos.get(br.b_idx);
              if (!a || !b) return null;
              if (br.confidence === "coincidence")
                return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#8a86b8" strokeWidth={0.5} strokeOpacity={0.05} />;
              if (br.confidence === "medium")
                return (
                  <line
                    key={i}
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                    stroke={br.shape_fires ? COLD : WARM}
                    strokeWidth={1}
                    strokeOpacity={0.22}
                    strokeDasharray={br.dissent ? "3 4" : undefined}
                  />
                );
              // high = both channels fired → a verified nexus; the only thing allowed to glow
              return (
                <line
                  key={i}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke="#f5f7ff"
                  strokeWidth={2.2}
                  strokeOpacity={0.95}
                  filter="url(#nexglow)"
                />
              );
            })}
            {/* domain stars */}
            {data.A.units.map((u) => {
              const p = layout.aPos.get(u.idx)!;
              return <circle key={`a${u.idx}`} cx={p.x} cy={p.y} r={u.anchor ? 4.5 : 2.6} fill={COLD} fillOpacity={u.anchor ? 0.95 : 0.5} filter={u.anchor ? "url(#nexglow)" : undefined} />;
            })}
            {data.B.units.map((u) => {
              const p = layout.bPos.get(u.idx)!;
              return <circle key={`b${u.idx}`} cx={p.x} cy={p.y} r={u.anchor ? 4.5 : 2.6} fill={WARM} fillOpacity={u.anchor ? 0.95 : 0.5} filter={u.anchor ? "url(#nexglow)" : undefined} />;
            })}
            <text x={250} y={44} className="pr-nexus-domlabel" textAnchor="middle" fill={COLD}>
              {data.A.prefix} · {data.A.metric}
            </text>
            <text x={W - 250} y={44} className="pr-nexus-domlabel" textAnchor="middle" fill={WARM}>
              {data.B.prefix} · {data.B.metric}
            </text>
          </svg>

          {sc && (
            <div className="pr-nexus-hud">
              <h4>诚实计分板</h4>
              <dl>
                <div><dt>候选桥</dt><dd>{sc.candidates}</dd></div>
                <div className="pr-hud-high"><dt>真桥（双渠道点亮）</dt><dd>{sc.high}</dd></div>
                <div><dt>单渠道（异议）</dt><dd>{sc.medium}</dd></div>
                <div><dt>巧合（虚影）</dt><dd>{sc.coincidence}</dd></div>
                <div><dt>实际耦合数</dt><dd>{sc.true_couplings}</dd></div>
                <div><dt>点亮集精度</dt><dd>{sc.high_tier_precision == null ? "—" : sc.high_tier_precision}</dd></div>
              </dl>
              <p className="pr-nexus-caveat">{data.caveat}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
