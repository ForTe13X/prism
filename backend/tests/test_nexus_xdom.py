"""Phase-B.0 — the dual-domain coupled substrate + the channel-blind §6c gate. These pin the panel-vetted
foundation BEFORE any channel exists: the two domains are token-disjoint (Phase-A's string winner dies
cross-domain), the shape⊥attribute factorization is mechanically real (changing one latent leaves the other
store byte-identical), the §6c gate passes (an oracle recovers the coupling while time/depth/string are
~chance), and everything is deterministic with the eval label never leaking onto a scorer's bridge."""
from __future__ import annotations

from backend.app.data_package_xdom import KNOBS, _build_domain, _profile, generate_xdom
from backend.app.nexus_substrate import _tokens
from backend.app.nexus_xdom_gate import run_gate
from backend.app.nexus_xdom_substrate import (
    candidate_bridges_xdom, labelled_bridges_xdom, rewired_coupling,
)

SEEDS = [f"xd-{i}" for i in range(60)]


def _domain_tokens(domain):
    toks = set()
    for u in domain["units"]:
        toks |= set(_tokens(u["id"]))
        for r in u["records"]:
            toks |= _tokens(r["cat"])
    return toks


def test_domains_are_token_disjoint():
    # the whole point of Phase B: you cannot cross-domain string-match, so Phase-A's semantic winner is
    # structurally 0 here. Coupled pairs are (i,i) by position — the id_offset keeps even the id numbers
    # disjoint, so no token bridges the domains.
    g = generate_xdom("xd-0")
    assert _domain_tokens(g["A"]).isdisjoint(_domain_tokens(g["B"]))


def test_shape_and_attribute_latents_are_mechanically_decoupled():
    # the independence PRIMITIVE: the series depends only on the shape profile, the attributes only on theta.
    prof = _profile("s", "prof", 0)
    prof2 = _profile("s", "prof", 1)
    base = [{"i": 0, "j": 0, "prof": prof, "fa": 26, "fb": 26, "theta": [0.1] * 6}]
    diff_theta = [{"i": 0, "j": 0, "prof": prof, "fa": 26, "fb": 26, "theta": [-0.3, 0.4, 0.0, 0.2, -0.1, 0.1]}]
    diff_prof = [{"i": 0, "j": 0, "prof": prof2, "fa": 26, "fb": 26, "theta": [0.1] * 6}]

    d0 = _build_domain("s", "A", base, [])
    d_theta = _build_domain("s", "A", diff_theta, [])
    d_prof = _build_domain("s", "A", diff_prof, [])
    uid = d0["units"][0]["id"]
    cats0 = [r["cat_index"] for r in d0["units"][0]["records"]]
    cats_theta = [r["cat_index"] for r in d_theta["units"][0]["records"]]
    cats_prof = [r["cat_index"] for r in d_prof["units"][0]["records"]]

    assert d0["series"][uid] == d_theta["series"][uid]    # changing theta does NOT touch the series
    assert cats0 != cats_theta                            # ...but it DOES change the attributes
    assert d0["series"][uid] != d_prof["series"][uid]     # changing the profile DOES change the series
    assert cats0 == cats_prof                             # ...and does NOT touch the attributes

    # AND it must still hold under the same-unit COLLISION that occurs in real packages (a distractor
    # landing on a coupled unit superimposes a 2nd dip + 2nd theta on the same series/logits).
    dist = [{"side": "A", "unit": 0, "prof": _profile("s", "dprof", 0), "f": 30, "theta": [0.2] * 6}]
    c_base = _build_domain("s", "A", base, dist)
    c_theta = _build_domain("s", "A", diff_theta, dist)        # only the coupled theta differs
    c_prof = _build_domain("s", "A", diff_prof, dist)          # only the coupled profile differs
    assert c_base["series"][uid] == c_theta["series"][uid]     # under collision: theta still ⊥ series
    assert [r["cat_index"] for r in c_base["units"][0]["records"]] != \
           [r["cat_index"] for r in c_theta["units"][0]["records"]]
    assert c_base["series"][uid] != c_prof["series"][uid]      # profile still drives the series
    assert [r["cat_index"] for r in c_base["units"][0]["records"]] == \
           [r["cat_index"] for r in c_prof["units"][0]["records"]]


def test_candidates_labelled_observation_only():
    g = generate_xdom("xd-1")
    bridges, ctx = candidate_bridges_xdom(g)
    assert bridges and any(b["y"] == 1 for b in bridges) and any(b["y"] == 0 for b in bridges)
    for b in bridges:
        assert "coupling" not in b and "_latents" not in b and "theta" not in b  # no truth leak
        assert len(b["a_hist"]) == len(b["b_hist"]) == KNOBS["n_cats"]  # observation histograms present


def test_s6c_gate_passes_channel_blind():
    r = run_gate(SEEDS)
    assert r["gate_pass"] is True
    assert r["oracle_auc"] >= 0.95                        # the truth is recoverable
    assert 0.40 <= r["time_auc"] <= 0.60                  # timing necessary-but-insufficient
    assert 0.40 <= r["depth_auc"] <= 0.60                 # fixed-depth: candidacy can't read the shape
    assert 0.40 <= r["string_auc"] <= 0.60                # strings can't cross domains
    assert r["n_positives"] >= 100                        # enough positives at >=60 seeds to read AUC


def test_rewire_and_distractor_controls():
    g = generate_xdom("xd-2")
    rew = rewired_coupling(g)
    assert all(p not in set(g["coupling"]) for p in rew)  # every rewired pair is a non-true pair
    distractor = labelled_bridges_xdom(SEEDS[:10], control="distractor_only")
    assert distractor and all(b["y"] == 0 for b in distractor)  # a set with NO real bridges


def test_deterministic():
    assert generate_xdom("xd-5") == generate_xdom("xd-5")
    assert run_gate(SEEDS[:20]) == run_gate(SEEDS[:20])


def test_api_xdom_gate():
    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)
    r = client.get("/api/nexus_xdom/gate")
    assert r.status_code == 200 and r.json()["gate_pass"] is True
