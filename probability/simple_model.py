"""
SimpleModel — lightweight probability estimate for price prediction markets.

Uses: distance to target (%), time to expiry, and rolling volatility.
No external data required beyond BTC spot price.

Formula (logistic approximation):
  z = -|distance_pct| / (volatility * sqrt(T_hours / 24))
  prob_cross = 1 / (1 + exp(-z * k))   where k is a scaling constant

  If direction == "above" and current > target: shift up.
  If direction == "above" and current < target: shift down.

This is a rough but fast heuristic — replace with Monte Carlo once validated.
"""

import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_K = 3.0  # logistic steepness — tune based on backtesting


def estimate(
    current_price: float,
    target_price: float,
    direction: str,             # "above" | "below"
    hours_to_expiry: float,
    annualized_volatility: float,
) -> Optional[float]:
    if hours_to_expiry <= 0 or annualized_volatility <= 0 or current_price <= 0:
        return None

    # Normalised distance: how many daily-vol units away is the target?
    daily_vol = annualized_volatility / math.sqrt(365)
    period_vol = daily_vol * math.sqrt(hours_to_expiry / 24)

    if period_vol == 0:
        return None

    log_return_needed = math.log(target_price / current_price)
    z = log_return_needed / period_vol  # positive = target above current

    # Standard normal CDF approximation (Abramowitz & Stegun)
    prob_above = _norm_cdf(z)

    if direction == "above":
        prob = 1.0 - prob_above   # P(price ends above target)
    else:
        prob = prob_above          # P(price ends below target)

    prob = max(0.02, min(0.98, prob))
    logger.debug(
        "SimpleModel: S=%.2f K=%.2f dir=%s T=%.1fh σ=%.2f z=%.3f → %.3f",
        current_price, target_price, direction, hours_to_expiry, annualized_volatility, z, prob,
    )
    return prob


def _norm_cdf(x: float) -> float:
    """Approximation of standard normal CDF."""
    return 0.5 * math.erfc(-x / math.sqrt(2))
