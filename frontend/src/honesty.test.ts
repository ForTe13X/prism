import { describe, expect, it } from "vitest";

// OBSERVER §15 P0-3 (zero-dependency fallback): the summary panels are never render-tested, so a "tidy the
// copy" edit could silently delete a load-bearing caveat with CI green. Numbers are API-locked elsewhere;
// this locks the caveat TEXT at the source level — a tripwire against accidental softening, not a proof.
// Uses Vite's import.meta.glob raw import (no node:fs ⇒ no new devDep, type-checked via vite/client).
const SRC = import.meta.glob("./*.tsx", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
const nexus = SRC["./NexusView.tsx"];
const axiom = SRC["./AxiomGainView.tsx"];

describe("caveat-text tripwire", () => {
  it("NexusView keeps collapse + ceiling + single-view + dual-control caveats", () => {
    expect(nexus).toContain("非生产证据"); // overall honest boundary
    expect(nexus).toContain("塌"); // Track-1 real-calibration collapse
    expect(nexus).toContain("单数据集多视图"); // §8j real-coupling boundary (was dropped — P0-2a)
    expect(nexus).toContain("rewire"); // §14 dual-control disclosure (was a construct-swap — P0-1b)
    expect(nexus).toContain("天花板"); // card ② ceiling banner (P0-2b)
  });

  it("the win card never renders without a ceiling (≥3 is-caveat cards)", () => {
    expect((nexus.match(/is-caveat/g) || []).length).toBeGreaterThanOrEqual(3);
  });

  it("AxiomGainView keeps the synthetic + token-only honest boundary", () => {
    expect(axiom).toContain("合成"); // small-scale synthetic data
    expect(axiom).toContain("token"); // local models $=0 ⇒ token-only cost axis
  });
});
