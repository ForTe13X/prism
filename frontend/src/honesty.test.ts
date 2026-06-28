import { describe, expect, it } from "vitest";

// OBSERVER §15 P0-3 (zero-dependency fallback): the summary panels are never render-tested, so a "tidy the
// copy" edit could silently delete a load-bearing caveat with CI green. Numbers are API-locked elsewhere;
// this locks the caveat TEXT at the source level — a tripwire against accidental softening, not a proof.
// Uses Vite's import.meta.glob raw import (no node:fs ⇒ no new devDep, type-checked via vite/client).
const SRC = import.meta.glob("./*.tsx", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
const nexus = SRC["./NexusView.tsx"];
const axiom = SRC["./AxiomGainView.tsx"];
// Strip /* */ and whole-line // comments so a caveat that survives only inside a comment can't satisfy the
// tripwire — the strings must appear in RENDERED JSX, not a doc-comment (anchored // avoids eating "https://" etc.)
const stripComments = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const axiomRendered = stripComments(axiom);

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

  it("the H2 money-moment (③) keeps its Tier-2 frontier + structural-flat caveats", () => {
    // the genuine-frontier GPT-5.5 point is a browser-captured, non-reproducible Tier-2 single point — these
    // strings must ride with it where the eye lands, never softened into a clean "law" (OBSERVER P1 audit fix).
    // Asserted against the COMMENT-STRIPPED source so a caveat that survives only in a comment can't pass.
    expect(axiomRendered).toContain("浏览器抓取"); // Tier-2 provenance (chip + verdict)
    expect(axiomRendered).toContain("不可复现"); // not re-runnable against a pinned model
    expect(axiomRendered).toContain("未测 token"); // H2b is UNMEASURED for the frontier point (token not exposed by web UI)
    expect(axiomRendered).toContain("Spearman"); // read the directional rank corr, not the brittle monotone bool
    expect(axiomRendered).toContain("内点、非更强模型"); // qwen3.6 wobble is RENDERED + disclosed, not pruned (DON'T #4)
    expect(axiomRendered).toContain("推断"); // the flat-line's frontier continuation is inference (drawn dashed), not measured
  });
});
