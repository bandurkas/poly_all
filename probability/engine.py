"""
ProbabilityEngine — ensemble model dispatcher.

Routes each market to the appropriate sub-models based on market_type,
then combines with weighted ensemble from config.MODEL_WEIGHTS.
"""

import logging
from typing import Optional

import config
from probability.models.market_implied import MarketImpliedModel
from probability.models.volatility import VolatilityModel
from probability.models.historical import HistoricalModel
from probability.models.momentum import MomentumModel

logger = logging.getLogger(__name__)


class ProbabilityEngine:
    def __init__(self):
        self.market_implied = MarketImpliedModel()
        self.volatility = VolatilityModel()
        self.historical = HistoricalModel()
        self.momentum = MomentumModel()

    async def calculate(self, market) -> Optional[float]:
        weights = config.MODEL_WEIGHTS.get(market.market_type, config.MODEL_WEIGHTS["unknown"])

        results = {}

        if weights["market_implied"] > 0:
            results["market_implied"] = self.market_implied.predict(market)

        if weights["volatility"] > 0:
            results["volatility"] = await self.volatility.predict(market)

        if weights["historical"] > 0:
            results["historical"] = await self.historical.predict(market)

        if weights["momentum"] > 0:
            results["momentum"] = self.momentum.predict(market)

        # Weighted ensemble
        total_weight = 0.0
        weighted_sum = 0.0
        for key, prob in results.items():
            if prob is None:
                continue
            w = weights[key]
            weighted_sum += prob * w
            total_weight += w

        if total_weight == 0:
            return None

        final = weighted_sum / total_weight
        logger.debug(
            "Probability for %s (%s): %.3f | components=%s",
            market.market_id, market.market_type, final, results,
        )
        return final
