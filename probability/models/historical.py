"""
Model 2 — Historical Base Rate.

For price_prediction markets: looks up historical outcomes for similar
setups (same asset, similar price distance %, similar time to expiry,
similar volatility regime) from the PostgreSQL history table.

Returns None if insufficient history (< 30 samples).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

MIN_SAMPLES = 30


class HistoricalModel:
    async def predict(self, market) -> Optional[float]:
        # TODO: query PostgreSQL for historical outcomes matching:
        #   - same market_type
        #   - similar price_distance_pct (±5%)
        #   - similar hours_to_expiry (±20%)
        #   - similar volatility regime
        # SELECT AVG(outcome) FROM trades WHERE ... LIMIT 500
        logger.debug("HistoricalModel: not yet implemented for %s", market.market_id)
        return None
