"""Read API for the split-from-shared-latent substrate (DESIGN_data_package §11). Deterministic/offline.
The public view strips all eval-only latents; the gate proves the substrate is well-posed + non-leaky."""
from __future__ import annotations

from fastapi import APIRouter

from .data_package_split import generate_split, public_view
from .split_gate import run_split_gate

split_router = APIRouter(prefix="/api/split", tags=["split"])


@split_router.get("/view")
def split_view(seed: str = "sp-0") -> dict:
    """One split package as a downstream consumer sees it — two domains of records (eval-only latents
    stripped, NO twin map). Same latent entity looks different across domains (variant transform)."""
    return public_view(generate_split(seed))


@split_router.get("/gate")
def split_gate(seeds: int = 40) -> dict:
    """§6c discriminability gate: oracle recovers the true twins, surface/value matchers are ~chance
    (non-leaky), a z-scored semantic matcher recovers (solvable), twins are sparse. Honest: known-truth
    but CONSTRUCTED coupling — external validity raised, not closed."""
    return run_split_gate([f"sp-{i}" for i in range(max(1, min(seeds, 100)))])   # clamp: bounded public GET
