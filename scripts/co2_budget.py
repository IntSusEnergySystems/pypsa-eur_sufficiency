# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

CO2_LIMIT_PREFIX = "CO2Limit"


def co2_limit_name(bound: str, horizon: int | None = None) -> str:
    """Return the name of the CO2 global constraint for a bound and horizon."""
    name = f"{CO2_LIMIT_PREFIX}-{bound}"
    return name if horizon is None else f"{name}-{horizon}"


def bound_value_for_horizon(bound: Any, current_horizon: int) -> float | None:
    if bound is None:
        return None
    if isinstance(bound, (int, float)):
        return float(bound)
    if isinstance(bound, Mapping):
        if current_horizon in bound:
            value = bound[current_horizon]
            if value is None:
                return None
            return float(value)
        horizon_str = str(current_horizon)
        if horizon_str in bound:
            value = bound[horizon_str]
            if value is None:
                return None
            return float(value)
        return None
    raise TypeError(
        "co2_budget bounds must be null, a number, or a dict mapping year to value. "
        f"Received {type(bound).__name__}."
    )


def co2_budget_for_horizon(
    co2_budget: dict,
    *,
    current_horizon: int,
    baseline_1990: float | None = None,
) -> tuple[float | None, float | None]:
    relative = co2_budget["relative"]

    upper_raw = co2_budget["upper"]
    lower_raw = co2_budget["lower"]

    upper = bound_value_for_horizon(upper_raw, current_horizon)
    lower = bound_value_for_horizon(lower_raw, current_horizon)

    if relative and (upper is not None or lower is not None):
        if baseline_1990 is None:
            raise ValueError(
                "co2_budget.relative is true but no 1990 baseline emissions were provided."
            )
        if upper is not None:
            upper *= baseline_1990
        if lower is not None:
            lower *= baseline_1990

    if lower is not None and upper is not None and lower >= upper:
        raise ValueError(
            f"Lower bound ({lower}) must be less than upper bound ({upper}) "
            f"for horizon {current_horizon}."
        )

    return upper, lower


def lulucf_sink_credit(lulucf: pd.Series) -> float:
    """Return the LULUCF sink credited to a CO2 budget.

    Units follow ``lulucf`` (megatonnes in the CO2 totals file). Positive
    LULUCF, a source, is set to zero. Negative values, a sink, are
    sign-flipped and summed. This is the adjustment from the previous
    global CO2 constraint, and it is not scaled by the 1990 reduction factor.
    """
    return float((-lulucf.clip(upper=0)).sum())


def add_lulucf_credit(
    upper: float | None,
    lower: float | None,
    credit: float,
) -> tuple[float | None, float | None]:
    """Add a LULUCF sink credit to each active CO2 bound.

    ``credit`` is in the same units as the bounds. Both bounds move by the
    same amount, so a feasible gap between them stays feasible.
    """
    if upper is not None:
        upper = upper + credit
    if lower is not None:
        lower = lower + credit
    if lower is not None and upper is not None and lower >= upper:
        raise ValueError(
            f"Lower bound ({lower}) must be less than upper bound ({upper}) "
            "after adding the LULUCF credit."
        )
    return upper, lower
