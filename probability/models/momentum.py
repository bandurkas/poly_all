"""
Model 4 — Momentum Model.

Signals that recent price movement and volume growth suggest
the market is moving toward YES or NO resolution.

Adjusts base probability (market implied) by momentum factors:
  - price_change_1h:  recent directional move
  - volume_change_1h: increasing participation = conviction

Returns None if no momentum data available.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

MOMENTUM_WEIGHT = 0.10   # max ±10% adjustment from momentum


class MomentumModel:
    def predict(self, market) -> Optional[float]:
        base = market.yes_price
        if base is None:
            return None

        extra = market.extra
        price_change = extra.get("price_change_1h")    # e.g. +0.05 = +5¢
        volume_change = extra.get("volume_change_1h")  # e.g. +0.30 = +30%

        if price_change is None:
            return None

        # Positive price change + rising volume → bullish momentum
        momentum_signal = price_change
        if volume_change is not None and volume_change > 0:
            momentum_signal *= (1 + min(volume_change, 1.0))

        adjustment = max(-MOMENTUM_WEIGHT, min(MOMENTUM_WEIGHT, momentum_signal))
        prob = float(base) + adjustment
        return max(0.01, min(0.99, prob))
