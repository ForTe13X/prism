"""Tamper-evident lock on the preserved GPT-5.5 browser-frontier capture (docs/provenance/). The point is a
Tier-2 browser capture (not reproducible against the model), but the SCORING of its preserved answers IS
reproducible: re-score each captured answer against the project's score() + the frozen ground-truths and assert
the recorded F1 + the §11e headline (naive mean 0.950, axiom 1.000) hold. If anyone edits the captured answers
or truths, this test fails — so the preserved provenance can't silently drift from what the docs claim."""
from __future__ import annotations

import json
import pathlib

from backend.app.data_package_eval import score

_ARTIFACT = pathlib.Path(__file__).resolve().parents[2] / "docs" / "provenance" / "gpt5_5_frontier_capture.json"


def test_gpt5_capture_scores_match_recorded_and_s11e():
    art = json.loads(_ARTIFACT.read_text(encoding="utf-8"))
    naive = []
    for cell in art["cells"]:
        f1 = round(score(cell["gpt5_5_answer"], cell["ground_truth"])["f1"], 3)
        assert f1 == cell["f1"], f"{cell['seed']}/{cell['condition']}: re-scored {f1} != recorded {cell['f1']}"
        if cell["condition"] == "naive":
            naive.append(f1)
    # the §11e headline, recomputed from the preserved answers — browser capture, but the scoring is auditable
    assert round(sum(naive) / len(naive), 3) == 0.95 == art["aggregate"]["naive_mean_f1"]
    assert art["aggregate"]["axiom_f1_ho0"] == 1.0
    # provenance honesty: it must stay labelled Tier-2 / browser / not-API and carry the no-token-counts caveat
    meta = art["metadata"]
    assert "Tier-2" in meta["tier"] and "NOT API" in meta["source"]
    assert "UNMEASURED" in meta["no_token_counts"]
