"""Phase-B cross-domain coupled substrate (METRIC_nexus_reality §4 Phase B) — deterministic, clean-room.

Phase A proved the single-domain substrate makes the real bridge a temporal coincidence by construction, so
"convergent validity" there was one token table read three times. Phase B fixes that: TWO disjoint-namespace
domains (INFRA load × LIBRARY circulation) joined by an eval-only coupling, engineered SO THAT a true
cross-domain nexus SHOULD be recoverable via ≥2 observed channels living in disjoint stores — and is NOT
recoverable from timing (proven here by the §6c gate; the channel scorers themselves are Phase-B.1, not yet
in the tree). "Disjoint stores" is a mechanical DESIGN property (test-backed); whether the channels are
genuinely independent AND informative is what Phase-B.1 measures.

The independence primitive (design panel, empirically validated): per incident k, draw TWO factored latents
from DISJOINT _unit sub-keys —
  * a SHAPE profile (a normalized per-frame dip vector) injected into BOTH endpoints' metric series, at
    PER-ENDPOINT INDEPENDENT frames f_A,f_B (so coupled endpoints share the shape but NOT the timestamp →
    the |Δframe| baseline is ~chance); the dip's centre is its deepest point (anchor==f) and its depth is
    FIXED (m-independent), so the depth/candidacy baseline cannot read the shape (the collider is broken);
  * a THETA attribute offset that shifts each endpoint unit's categorical record distribution IDENTICALLY
    (index-aligned across the two domains, different category NAMES) → a distributional fingerprint match
    that is never a string match.
The two latents live in disjoint stores (timeseries vs SQL records) and disjoint dtypes, so the shape and
fingerprint channels (Phase-B.1) read non-overlapping evidence. Constants are FROZEN in ``KNOBS`` and the
difficulty is pre-registered CHANNEL-BLIND (oracle recovers; time/depth/string baselines ~chance) before any
channel scorer exists.
"""
from __future__ import annotations

from .data_synth import _unit

# FROZEN knobs (pre-registered difficulty; validated over >=60 seeds). The channel scorers (Phase-B.1) must
# NOT import or tune these — difficulty is fixed channel-blind.
# HONESTY (§6c reverse-trap): these were NOT frozen purely channel-blind — during design the shape/attr
# constants (depth, half_width, attr_shift, records_per_unit) were explored WITH visibility of the probe
# channel AUCs to ensure adequate power, so "the channels are informative" is engineered, not discovered.
# The committed §6c GATE (nexus_xdom_gate, oracle vs baselines) IS channel-blind; what stays falsifiable is
# channel INDEPENDENCE and the convergence MARGIN (neither was tuned). Phase-B.1 must not tune these further.
KNOBS = {
    "n_units": 16, "frames": 64, "k_true": 10, "n_distractor": 14,
    "band_lo": 24, "band_span": 8, "n_cats": 6, "records_per_unit": 40,
    "base": 250.0, "wiggle": 8.0, "depth": 180.0, "half_width": 6, "attr_shift": 3.0,
    "candidacy_dip_frac": 0.7,  # a unit is an anchor iff its in-band min < frac*mean
}

# two DISJOINT-namespace domains. Category NAMES are domain-specific (so a string match across domains is
# impossible) but POSITION-aligned (index c in INFRA corresponds to index c in LIBRARY) — that index
# alignment is the only cross-domain assumption, and it is distributional, never lexical.
# id_offset keeps the two domains' id NUMBERS disjoint too (coupled pairs are (i,i) by position, so equal
# suffixes would leak the alignment to a string matcher; IN-001 vs LB-101 share no token).
DOMAINS = {
    "A": {"prefix": "IN", "metric": "load", "id_offset": 0,
          "cats": ["cpu", "mem", "disk", "net", "iops", "gpu"]},
    "B": {"prefix": "LB", "metric": "circulation", "id_offset": 100,
          "cats": ["fiction", "poetry", "drama", "essay", "atlas", "manual"]},
}


def _u(seed: str, *parts: object) -> float:
    return _unit(seed, *parts)


def _band_frame(seed: str, *parts: object) -> int:
    return KNOBS["band_lo"] + int(_u(seed, *parts) * KNOBS["band_span"]) % KNOBS["band_span"]


def _profile(seed: str, tag: str, k: int) -> list[float]:
    """A dip profile of length 2*HW+1 whose CENTRE is the deepest (==1, so argmin==injection frame and
    depth is shape-independent); off-centre values in [0.3,0.9] carry the discriminative signature."""
    hw = KNOBS["half_width"]
    prof = [0.3 + 0.6 * _u(seed, tag, k, t) for t in range(2 * hw + 1)]
    prof[hw] = 1.0
    return prof


def _softmax(xs: list[float]) -> list[float]:
    import math
    m = max(xs)
    es = [math.exp(x - m) for x in xs]
    s = sum(es)
    return [e / s for e in es]


def _incidents(seed: str) -> tuple[list, list]:
    """Coupled incidents k → (unit i(k)=k in A, unit j(k)=k in B), each with a shared shape profile + theta
    and PER-ENDPOINT frames. Plus one-sided distractors (deform only A or only B — hard temporal negatives)."""
    nc = KNOBS["n_cats"]
    coupled = []
    for k in range(KNOBS["k_true"]):
        coupled.append({
            "i": k, "j": k, "prof": _profile(seed, "prof", k),
            "fa": _band_frame(seed, "frmA", k), "fb": _band_frame(seed, "frmB", k),
            "theta": [_u(seed, "attr", k, c) - 0.5 for c in range(nc)],
        })
    distractor = []
    n = KNOBS["n_units"]
    for d in range(KNOBS["n_distractor"]):
        side = "A" if _u(seed, "dside", d) < 0.5 else "B"
        distractor.append({
            "side": side, "unit": int(_u(seed, "dunit", d) * n) % n,
            "prof": _profile(seed, "dprof", d), "f": _band_frame(seed, "dfrm", d),
            "theta": [_u(seed, "dattr", d, c) - 0.5 for c in range(nc)],
        })
    return coupled, distractor


def _build_domain(seed: str, dk: str, coupled: list, distractor: list) -> dict:
    base, wig, depth, hw = KNOBS["base"], KNOBS["wiggle"], KNOBS["depth"], KNOBS["half_width"]
    nf, nc, nrec = KNOBS["frames"], KNOBS["n_cats"], KNOBS["records_per_unit"]
    spec = DOMAINS[dk]
    endpoint = (lambda inc: inc["i"]) if dk == "A" else (lambda inc: inc["j"])
    units, series = [], {}
    for uu in range(KNOBS["n_units"]):
        uid = f"{spec['prefix']}-{spec['id_offset'] + uu + 1:03d}"
        s = [base + wig * (_u(seed, dk, "wig", uu, t) - 0.5) * 2 for t in range(nf)]
        logits = [(_u(seed, dk, "abase", uu, c) - 0.5) for c in range(nc)]
        for inc in coupled:
            if endpoint(inc) == uu:
                f = inc["fa"] if dk == "A" else inc["fb"]
                for τ in range(2 * hw + 1):
                    if 0 <= f - hw + τ < nf:
                        s[f - hw + τ] -= depth * inc["prof"][τ]
                logits = [logits[c] + KNOBS["attr_shift"] * inc["theta"][c] for c in range(nc)]
        for dd in distractor:
            if dd["side"] == dk and dd["unit"] == uu:
                f = dd["f"]
                for τ in range(2 * hw + 1):
                    if 0 <= f - hw + τ < nf:
                        s[f - hw + τ] -= depth * dd["prof"][τ]
                logits = [logits[c] + KNOBS["attr_shift"] * dd["theta"][c] for c in range(nc)]
        p = _softmax(logits)
        # R records per unit, each a categorical draw → the observed attribute distribution (a thin sample
        # of the latent theta-shifted multinomial). Category NAMES are domain-specific (string-disjoint).
        records = []
        for r in range(nrec):
            x = _u(seed, dk, "rec", uu, r)
            acc, ci = 0.0, nc - 1
            for c in range(nc):
                acc += p[c]
                if x <= acc:
                    ci = c
                    break
            records.append({"cat_index": ci, "cat": spec["cats"][ci]})
        units.append({"id": uid, "records": records})
        series[uid] = s
    return {"domain": dk, "prefix": spec["prefix"], "metric": spec["metric"], "cats": spec["cats"],
            "units": units, "series": series}


def generate_xdom(seed: str) -> dict:
    """Two coupled domains + the eval-only coupling table and latents (for the oracle). Deterministic."""
    coupled, distractor = _incidents(seed)
    A = _build_domain(seed, "A", coupled, distractor)
    B = _build_domain(seed, "B", coupled, distractor)
    coupling = sorted({(inc["i"], inc["j"]) for inc in coupled})
    return {
        "seed": seed, "A": A, "B": B,
        "coupling": coupling,                 # eval-only: set of (i_index, j_index) true cross-domain pairs
        "_latents": {"coupled": coupled, "distractor": distractor},  # eval-only: oracle's view
    }
