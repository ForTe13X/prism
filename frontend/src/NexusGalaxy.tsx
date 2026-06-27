import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import * as THREE from "three";
import type { NexusAlign, NexusBridge, NexusView as NexusViewData, NexusUnit } from "./types";

// The 3D "galaxy collision" — the stunning form of the SVG nexus view (DESIGN_visual_fusion §1). Every
// channel maps a real quantity: a bridge GLOWS (blooms) iff it cleared the metric (≥2/3 vote statically, or
// enough Sinkhorn transport mass during the alignment replay), so light == verified bridges (§6). Ghosts /
// medium are dim and CANNOT pass the bloom threshold. In replay mode the two galaxies start APART and
// collide as the real residual converges — animation == real alignment, never a scripted keyframe.
const COLD = new THREE.Color("#39a7c8");
const WARM = new THREE.Color("#d29240");
const HOT = new THREE.Color(2.4, 2.6, 3.0); // HDR white — the only thing bright enough to bloom
type Tier = "high" | "medium" | "coincidence";

// a two-arm spiral disc per cluster, offset to its side (× sepScale, the collision distance) and tilted
function unitPos(idx: number, n: number, side: "A" | "B", sepScale: number): THREE.Vector3 {
  const t = n > 1 ? idx / (n - 1) : 0.5;
  const arm = idx % 2;
  const ang = t * Math.PI * 2.1 + arm * Math.PI;
  const rad = 0.7 + t * 3.4;
  const cx = (side === "A" ? -5.2 : 5.2) * sepScale;
  const tilt = side === "A" ? 0.5 : -0.5;
  const lx = rad * Math.cos(ang);
  const ly = rad * Math.sin(ang);
  const pull = (side === "A" ? 1 : -1) * (1.6 - Math.abs(lx) * 0.18);
  return new THREE.Vector3(cx + pull + lx * 0.35, ly * 0.92, lx * 0.9 * tilt);
}

function Cluster({ units, side, base, sepScale }: { units: NexusUnit[]; side: "A" | "B"; base: THREE.Color; sepScale: number }) {
  const ref = useRef<THREE.InstancedMesh>(null);
  const positions = useMemo(() => units.map((u) => unitPos(u.idx, units.length, side, sepScale)), [units, side, sepScale]);
  useLayoutEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    const dummy = new THREE.Object3D();
    units.forEach((u, i) => {
      dummy.position.copy(positions[i]);
      dummy.scale.setScalar(u.anchor ? 0.17 : 0.085);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      mesh.setColorAt(i, base.clone().multiplyScalar(u.anchor ? 1.0 : 0.45)); // anchors brighter, still below bloom
    });
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [units, positions, base]);
  return (
    <instancedMesh ref={ref} args={[undefined, undefined, units.length]}>
      <sphereGeometry args={[1, 12, 12]} />
      <meshBasicMaterial toneMapped={false} />
    </instancedMesh>
  );
}

function Bridges({ data, sepScale, tierOf }: { data: NexusViewData; sepScale: number; tierOf: (b: NexusBridge) => Tier }) {
  const { ghost, medium, high } = useMemo(() => {
    const aPos = new Map<number, THREE.Vector3>();
    const bPos = new Map<number, THREE.Vector3>();
    data.A.units.forEach((u) => aPos.set(u.idx, unitPos(u.idx, data.A.units.length, "A", sepScale)));
    data.B.units.forEach((u) => bPos.set(u.idx, unitPos(u.idx, data.B.units.length, "B", sepScale)));
    const g: number[] = [], m: number[] = [], h: number[] = [];
    for (const br of data.bridges) {
      const a = aPos.get(br.a_idx), b = bPos.get(br.b_idx);
      if (!a || !b) continue;
      const arr = tierOf(br) === "high" ? h : tierOf(br) === "medium" ? m : g;
      arr.push(a.x, a.y, a.z, b.x, b.y, b.z);
    }
    return { ghost: new Float32Array(g), medium: new Float32Array(m), high: new Float32Array(h) };
  }, [data, sepScale, tierOf]);

  const seg = (arr: Float32Array, color: THREE.Color, opacity: number) => (
    <lineSegments>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[arr, 3]} count={arr.length / 3} />
      </bufferGeometry>
      <lineBasicMaterial color={color} transparent opacity={opacity} toneMapped={false} depthWrite={false} />
    </lineSegments>
  );
  return (
    <>
      {ghost.length > 0 && seg(ghost, new THREE.Color("#6a66a0"), 0.06)}
      {medium.length > 0 && seg(medium, new THREE.Color("#8f7bd0"), 0.32)}
      {high.length > 0 && seg(high, HOT, 0.98)}
    </>
  );
}

function Core({ high, reducedMotion }: { high: number; reducedMotion: boolean }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (ref.current) {
      const pulse = reducedMotion ? 0 : 0.03 * Math.sin(clock.elapsedTime * 1.6); // §7.4: static under reduced-motion
      ref.current.scale.setScalar(Math.max(0.05, 0.18 + 0.12 * high + pulse));
    }
  });
  if (high <= 0) return null;
  return (
    <mesh ref={ref}>
      <sphereGeometry args={[1, 24, 24]} />
      <meshBasicMaterial color={HOT} toneMapped={false} />
    </mesh>
  );
}

function Scene({ data, reducedMotion, sepScale, tierOf, highCount }:
  { data: NexusViewData; reducedMotion: boolean; sepScale: number; tierOf: (b: NexusBridge) => Tier; highCount: number }) {
  return (
    <>
      <color attach="background" args={["#05050b"]} />
      <Stars radius={60} depth={40} count={1400} factor={3} saturation={0} fade speed={0.4} />
      <Cluster units={data.A.units} side="A" base={COLD} sepScale={sepScale} />
      <Cluster units={data.B.units} side="B" base={WARM} sepScale={sepScale} />
      <Bridges data={data} sepScale={sepScale} tierOf={tierOf} />
      <Core high={highCount} reducedMotion={reducedMotion} />
      <OrbitControls enablePan={false} enableDamping minDistance={7} maxDistance={30}
        autoRotate={!reducedMotion} autoRotateSpeed={0.35} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.7} luminanceSmoothing={0.2} intensity={1.5} mipmapBlur />
      </EffectComposer>
    </>
  );
}

export default function NexusGalaxy({ data, align, step }: { data: NexusViewData; align?: NexusAlign | null; step?: number }) {
  const reducedMotion = typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const wrapRef = useRef<HTMLDivElement>(null);
  const setSizeRef = useRef<((w: number, h: number) => void) | null>(null);
  // Size the renderer EXPLICITLY from the wrapper (fixed CSS height) instead of relying on R3F's internal
  // ResizeObserver — that can read 0 on mount and never recover. Our own observer keeps it in sync.
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const apply = () => { setSizeRef.current?.(el.clientWidth, el.clientHeight); window.dispatchEvent(new Event("resize")); };
    const ro = new ResizeObserver(apply);
    ro.observe(el);
    // also nudge R3F's own measure at a few delays (its react-use-measure listens to window resize)
    const timers = [0, 80, 250, 600].map((d) => setTimeout(apply, d));
    return () => { ro.disconnect(); timers.forEach(clearTimeout); };
  }, []);

  // STATIC: separation 1, tiers from the ≥2/3 confidence. REPLAY: separation ∝ the live residual (galaxies
  // collide as it →0), tiers from this iteration's transport mass (bridges ignite as the plan concentrates).
  const { sepScale, tierOf, highCount } = useMemo(() => {
    if (!align || step == null || !align.snapshots.length) {
      return { sepScale: 1, tierOf: (b: NexusBridge) => b.confidence as Tier, highCount: data.scorecard.high };
    }
    const snap = align.snapshots[Math.max(0, Math.min(align.snapshots.length - 1, step))];
    const aiA = data.A.units.filter((u) => u.anchor).map((u) => u.idx).sort((x, y) => x - y);
    const biA = data.B.units.filter((u) => u.anchor).map((u) => u.idx).sort((x, y) => x - y);
    const tAt = (ai: number, bi: number) => {
      const x = aiA.indexOf(ai), y = biA.indexOf(bi);
      return x >= 0 && y >= 0 ? snap.transport[x]?.[y] ?? 0 : 0;
    };
    let maxT = 0;
    for (const br of data.bridges) maxT = Math.max(maxT, tAt(br.a_idx, br.b_idx));
    maxT = maxT || 1;
    const tierOf = (br: NexusBridge): Tier => {
      const t = tAt(br.a_idx, br.b_idx);
      return t >= 0.45 * maxT ? "high" : t >= 0.12 * maxT ? "medium" : "coincidence";
    };
    const sep = 1 + 1.25 * (snap.residual / (align.residuals[0] || 1)); // residual high → far apart
    return { sepScale: sep, tierOf, highCount: data.bridges.filter((b) => tierOf(b) === "high").length };
  }, [data, align, step]);

  return (
    <div className="pr-nexus-canvas-wrap" ref={wrapRef}>
      <Canvas camera={{ position: [0, 1.5, 18], fov: 50 }} dpr={[1, 2]} gl={{ antialias: true }}
              className="pr-nexus-canvas"
              onCreated={(state) => {
                setSizeRef.current = (w, h) => state.setSize(w, h);
                const el = wrapRef.current;
                if (el && el.clientWidth) state.setSize(el.clientWidth, el.clientHeight);
              }}>
        <Scene data={data} reducedMotion={!!reducedMotion} sepScale={sepScale} tierOf={tierOf} highCount={highCount} />
      </Canvas>
    </div>
  );
}
