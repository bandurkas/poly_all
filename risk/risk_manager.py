"""
RiskManager — position sizing and exposure limits.

Position sizing via Fractional Kelly Criterion:
  full_kelly = edge / (1 - market_price)    (for binary bet at market_price)
  size = full_kelly × KELLY_FRACTION × capital

Hard limits:
  - Max per trade: MAX_POSITION_PCT × capital
  - Max total open exposure: MAX_TOTAL_EXPOSURE_PCT × capital
"""

import logging
from dataclasses import dataclass
from typing import Optional

import config

logger = logging.getLogger(__name__)


@dataclass
class SizedSignal:
    signal: object
    bet_amount: float   # USD to risk


class RiskManager:
    def __init__(self):
        self._open_exposure: float = 0.0  # USD currently at risk

    def size(self, signal) -> Optional[SizedSignal]:
        capital = config.TOTAL_CAPITAL
        max_per_trade = capital * config.MAX_POSITION_PCT
        max_total = capital * config.MAX_TOTAL_EXPOSURE_PCT

        # Check total exposure headroom
        if self._open_exposure >= max_total:
            logger.debug("Skip: exposure %.2f >= max %.2f", self._open_exposure, max_total)
            return None

        # Fractional Kelly sizing
        p = signal.market_price
        edge = signal.edge
        if p >= 1.0:
            return None
        full_kelly = edge / (1 - p)
        kelly_size = full_kelly * config.KELLY_FRACTION * capital

        # Apply hard cap
        bet = min(kelly_size, max_per_trade, max_total - self._open_exposure)
        bet = round(bet, 2)

        if bet < config.MIN_BET:
            logger.debug("Skip: bet %.2f < min %.2f", bet, config.MIN_BET)
            return None

        logger.info(
            "Size: %s %s | edge=%.3f kelly_full=%.3f → bet=$%.2f",
            signal.direction, signal.market_id, edge, full_kelly, bet,
        )
        return SizedSignal(signal=signal, bet_amount=bet)

    def add_exposure(self, amount: float):
        self._open_exposure += amount

    def remove_exposure(self, amount: float):
        self._open_exposure = max(0.0, self._open_exposure - amount)
