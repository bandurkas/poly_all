"""
Model 1 — Market Implied Probability.
Simply returns the current YES price as the market's implied probability.
Baseline reference for edge calculation.
"""

from typing import Optional


class MarketImpliedModel:
    def predict(self, market) -> Optional[float]:
        if market.yes_price is None:
            return None
        return float(market.yes_price)
