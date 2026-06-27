"""Read API for the §4b real-calibration: fit a mechanism from a (synthetic-stand-in) reference's
aggregate statistics, re-sample, and report how reference vs calibrated match on FITTED and HELD-OUT
moments. See backend/app/calibration.py."""
from __future__ import annotations

from fastapi import APIRouter

from .calibration import IS_REAL_DATA, REFERENCE_LABEL, calibrate, moments

calibration_router = APIRouter(prefix="/api/calibration", tags=["calibration"])

_FITTED = ["x_mean", "x_std", "y_std", "corr_xy", "series_lag1", "y_over_x_std_ratio"]  # last = sanity (= y_std/x_std)
_HELD_OUT = ["x_skew", "series_std", "series_lag2", "series_lag3", "corr_x_series"]  # genuinely never fitted


@calibration_router.get("")
def calibration() -> dict:
    r = calibrate()
    ref_m, cal_m = moments(r["reference"]), moments(r["calibrated"])

    def cmp(keys: list[str]) -> dict:
        return {k: {"reference": round(ref_m[k], 3), "calibrated": round(cal_m[k], 3),
                    "abs_diff": round(abs(ref_m[k] - cal_m[k]), 3)} for k in keys}

    return {
        "is_real_data": IS_REAL_DATA, "reference_label": REFERENCE_LABEL,
        "fitted_params": r["params"].as_dict(),
        "fitted_moments": cmp(_FITTED),
        "held_out_moments": cmp(_HELD_OUT),
        "note": "reference 是真实数据的合成替身(IS_REAL_DATA=False)。只拟合聚合量(均值/方差/相关/AR(1));"
                "held-out 矩(未拟合)对得上 = 按检验真实,非按声称。诚实边界:简约机制只抓到二阶矩 + 线性耦合 + AR(1),"
                "更高阶分布形状(skew)未复刻。接真实数据需开放许可 + 只取聚合量。",
    }
