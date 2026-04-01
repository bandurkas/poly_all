"""
MarketScanner — filters and ranks markets for analysis.

Filters:
  1. Liquidity >= MIN_LIQUIDITY
  2. Volume 24h >= MIN_VOLUME_24H
  3. Days to expiry <= MAX_DAYS_TO_EXPIRY
  4. Spread <= MAX_SPREAD

Returns top TOP_MARKETS_COUNT by score.
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import config

if TYPE_CHECKING:
    from collector.market_collector import MarketSnapshot

logger = logging.getLogger(__name__)


class MarketScanner:
    def filter(self, markets: list) -> list:
        candidates = []
        for m in markets:
            if not self._passes_filters(m):
                continue
            score = self._score(m)
            candidates.append((score, m))

        candidates.sort(key=lambda x: x[0], reverse=True)
        top = [m for _, m in candidates[: config.TOP_MARKETS_COUNT]]
        logger.info("Scanner: %d → %d markets after filter", len(markets), len(top))
        return top

    # ── Filters ──────────────────────────────────────────────────────────────

    def _passes_filters(self, m) -> bool:
        if m.liquidity < config.MIN_LIQUIDITY:
            return False
        if m.volume_24h < config.MIN_VOLUME_24H:
            return False
        if m.spread > config.MAX_SPREAD:
            return False
        days = self._days_to_expiry(m.end_time)
        if days is None or days > config.MAX_DAYS_TO_EXPIRY:
            return False
        return True

    def _days_to_expiry(self, end_time: str) -> float | None:
        try:
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            delta = end - datetime.now(timezone.utc)
            return delta.total_seconds() / 86400
        except Exception:
            return None

    # ── Scoring ──────────────────────────────────────────────────────────────

    def _score(self, m) -> float:
        """Higher score = more interesting market."""
        volume_score = min(m.volume_24h / 10_000, 1.0)
        liquidity_score = min(m.liquidity / 5_000, 1.0)
        days = self._days_to_expiry(m.end_time) or 7
        urgency_score = 1.0 - (days / config.MAX_DAYS_TO_EXPIRY)
        spread_score = 1.0 - (m.spread / config.MAX_SPREAD)
        return (volume_score + liquidity_score + urgency_score + spread_score) / 4
