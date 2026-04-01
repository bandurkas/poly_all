"""
MispricingDetector — compares model probability vs market price.

Edge = model_prob − market_implied_prob

Only generates a signal if:
  - edge > MIN_EDGE
  - spread <= MAX_SPREAD
  - market probability is not extreme (5% < price < 95%) to avoid illiquid extremes
"""

import logging
from dataclasses import dataclass
from typing import Optional

import config

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    market_id: str
    market: object
    direction: str          # "YES" | "NO"
    market_price: float     # price to buy
    model_prob: float
    market_prob: float
    edge: float


class MispricingDetector:
    def evaluate(self, market, model_prob: float) -> Optional[Signal]:
        yes_price = market.yes_price
        no_price = market.no_price

        if yes_price is None or no_price is None:
            return None

        # Avoid extreme illiquid ends
        if yes_price < 0.05 or yes_price > 0.95:
            return None

        spread = market.spread
        if spread > config.MAX_SPREAD:
            logger.debug("Skip %s: spread %.3f > %.3f", market.market_id, spread, config.MAX_SPREAD)
            return None

        # Edge vs YES
        edge_yes = model_prob - yes_price
        # Edge vs NO (model says outcome is less likely than market thinks)
        edge_no = (1 - model_prob) - no_price

        if edge_yes >= edge_no and edge_yes >= config.MIN_EDGE:
            logger.info(
                "Signal YES | %s | edge=%.3f | model=%.3f market=%.3f",
                market.market_id, edge_yes, model_prob, yes_price,
            )
            return Signal(
                market_id=market.market_id,
                market=market,
                direction="YES",
                market_price=yes_price,
                model_prob=model_prob,
                market_prob=yes_price,
                edge=edge_yes,
            )

        if edge_no > edge_yes and edge_no >= config.MIN_EDGE:
            logger.info(
                "Signal NO  | %s | edge=%.3f | model=%.3f market=%.3f",
                market.market_id, edge_no, 1 - model_prob, no_price,
            )
            return Signal(
                market_id=market.market_id,
                market=market,
                direction="NO",
                market_price=no_price,
                model_prob=1 - model_prob,
                market_prob=no_price,
                edge=edge_no,
            )

        return None
