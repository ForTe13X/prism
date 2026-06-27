import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import * as THREE from "three";
import type { NexusView as NexusViewData, NexusUnit } from "./types";

// The 3D "galaxy collision" — the stunning form of the SVG nexus view (DESIGN_visual_fusion §1). Every
// channel maps a real quantity: a bridge GLOWS (blooms) iff it cleared the ≥2/3 vote (confidence "high"),
// so light == verified bridges (§6). Code-level ghosts/medium are dim and CANNOT pass the bloom threshold.
const COLD = new THREE.Color("#39a7c8");
const WARM = new THREE.Color("#d29240");
const HOT = new THREE.Color(2.4, 2.6, 3.0); // HDR white — the only thing bright enough to bloom

// a two-arm spiral disc per cluster, offset to its side and tilted, so the two galaxies face each other
function unitPos(idx: number, n: number, side: "A" | "B"): THREE.Vector3 {
  const t = n > 1 ? idx / (n - 1) : 0.5;
  const arm = idx % 2;
  const ang = t * Math.PI * 2.1 + arm * Math.PI;
  const rad = 0.7 + t * 3.4;
  const cx = side === "A" ? -5.2 : 5.2;
  const tilt = side === "A" ? 0.5 : -0.5;
  const lx = rad * Math.cos(ang);
  const ly = rad * Math.sin(ang);
  // pull the disc's leading edge toward the centre (the collision zone)
  const pull = (side === "A" ? 1 : -1) * (1.6 - Math.abs(lx) * 0.18);
  return new THREE.Vector3(cx + pull + lx * 0.35, ly * 0.92, lx * 0.9 * tilt);
}

function Cluster({ units, side, base }: { units: NexusUnit[]; side: "A" | "B"; base: THREE.Color }) {
  const ref = useRef<THREE.InstancedMesh>(null);
  const positions = useMemo(() => units.map((u) => unitPos(u.idx, units.length, side)), [units, side]);
  useLayoutEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    const dummy = new THREE.Object3D();
    units.forEach((u, i) => {
      const p = positions[i];
      dummy.position.copy(p);
      dummy.scale.setScalar(u.anchor ? 0.17 : 0.085);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      // anchors (units carrying a dip) glow brighter — but still below the bloom threshold (not "verified")
      mesh.setColorAt(i, base.clone().multiplyScalar(u.anchor ? 1.0 : 0.45));
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

function Bridges({ data }: { data: NexusViewData }) {
  const { ghost, medium, high } = useMemo(() => {
    const aPos = new Map<number, THREE.Vector3>();
    const bPos = new Map<number, THREE.Vector3>();
    data.A.units.forEach((u) => aPos.set(u.idx, unitPos(u.idx, data.A.units.length, "A")));
    data.B.units.forEach((u) => bPos.set(u.idx, unitPos(u.idx, data.B.units.length, "B")));
    const g: number[] = [], m: number[] = [], h: number[] = [];
    for (const br of data.bridges) {
      const a = aPos.get(br.a_idx), b = bPos.get(br.b_idx);
      if (!a || !b) continue;
      const arr = br.confidence === "high" ? h : br.confidence === "medium" ? m : g;
      arr.push(a.x, a.y, a.z, b.x, b.y, b.z);
    }
    return { ghost: new Float32Array(g), medium: new Float32Array(m), high: new Float32Array(h) };
  }, [data]);

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

// a white-hot core at the collision centre, scaled by the verified-bridge count (the merged nucleus)
function Core({ high, reducedMotion }: { high: number; reducedMotion: boolean }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (ref.current) {
      // honor prefers-reduced-motion (DESIGN §7.4: static after convergence) — freeze the breathing pulse
      const pulse = reducedMotion ? 0 : 0.03 * Math.sin(clock.elapsedTime * 1.6);
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

function Scene({ data, reducedMotion }: { data: NexusViewData; reducedMotion: boolean }) {
  return (
    <>
      <color attach="background" args={["#05050b"]} />
      <Stars radius={60} depth={40} count={1400} factor={3} saturation={0} fade speed={0.4} />
      <Cluster units={data.A.units} side="A" base={COLD} />
      <Cluster units={data.B.units} side="B" base={WARM} />
      <Bridges data={data} />
      <Core high={data.scorecard.high} reducedMotion={reducedMotion} />
      <OrbitControls enablePan={false} enableDamping minDistance={7} maxDistance={26}
        autoRotate={!reducedMotion} autoRotateSpeed={0.35} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.7} luminanceSmoothing={0.2} intensity={1.5} mipmapBlur />
      </EffectComposer>
    </>
  );
}

export default function NexusGalaxy({ data }: { data: NexusViewData }) {
  const reducedMotion = typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  // R3F measures its container via ResizeObserver; when it mounts during a tab switch the initial measure
  // can read 0 and stick at the 300×150 default. Nudge one resize once the layout has settled so it
  // re-measures to the wrapper's real size.
  useEffect(() => {
    const id = requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
    return () => cancelAnimationFrame(id);
  }, []);
  return (
    <div className="pr-nexus-canvas-wrap">
      <Canvas camera={{ position: [0, 1.5, 16], fov: 50 }} dpr={[1, 2]} gl={{ antialias: true }}
              className="pr-nexus-canvas">
        <Scene data={data} reducedMotion={!!reducedMotion} />
      </Canvas>
    </div>
  );
}
