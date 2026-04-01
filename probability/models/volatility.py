"""
Model 3 — Volatility-Based Probability (Monte Carlo).

Applicable to price_prediction markets only (BTC/ETH above/below a target).
Simulates SIMULATIONS price paths using current price + historical volatility,
counts how many end above/below the target.

market.extra expected keys:
  - current_price: float
  - target_price: float
  - direction: "above" | "below"
  - hours_to_expiry: float
  - annualized_volatility: float  (e.g. 0.80 for 80% annual vol)
"""

import logging
from typing import Optional

import numpy as np

import config

logger = logging.getLogger(__name__)


class VolatilityModel:
    async def predict(self, market) -> Optional[float]:
        extra = market.extra
        try:
            S = float(extra["current_price"])
            K = float(extra["target_price"])
            direction = extra["direction"]          # "above" | "below"
            T = float(extra["hours_to_expiry"]) / 8760  # convert to years
            sigma = float(extra["annualized_volatility"])
        except (KeyError, TypeError, ValueError):
            return None

        if T <= 0 or sigma <= 0 or S <= 0:
            return None

        rng = np.random.default_rng()
        drift = -0.5 * sigma ** 2 * T
        diffusion = sigma * np.sqrt(T) * rng.standard_normal(config.MONTE_CARLO_SIMULATIONS)
        end_prices = S * np.exp(drift + diffusion)

        if direction == "above":
            prob = float(np.mean(end_prices > K))
        else:
            prob = float(np.mean(end_prices < K))

        logger.debug(
            "VolatilityModel: S=%.2f K=%.2f dir=%s T=%.4f σ=%.2f → prob=%.3f",
            S, K, direction, T, sigma, prob,
        )
        return prob
