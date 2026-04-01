"""
MarketScanner — filters and ranks markets for analysis.

v1: BTC price prediction markets only.

Filters applied in order:
  1. Asset whitelist (ALLOWED_ASSETS)
  2. Market type = price_prediction
  3. Liquidity >= MIN_LIQUIDITY
  4. Volume 24h >= MIN_VOLUME_24H
  5. Days to expiry <= MAX_DAYS_TO_EXPIRY
  6. Spread <= MAX_SPREAD

Returns top TOP_MARKETS_COUNT by score.
"""

import logging
import re
from datetime import datetime, timezone

import config

logger = logging.getLogger(__name__)

# Patterns to identify price prediction markets from question text
_PRICE_PATTERNS = [
    re.compile(r"\b(BTC|Bitcoin)\b.*\b(above|below|over|under|higher|lower|\$[\d,]+)\b", re.IGNORECASE),
    re.compile(r"\b(ETH|Ethereum)\b.*\b(above|below|over|under|higher|lower|\$[\d,]+)\b", re.IGNORECASE),
    re.compile(r"\b(BTC|ETH)\b.*\bprice\b", re.IGNORECASE),
]

# Maps asset keyword → canonical name
_ASSET_KEYWORDS = {
    "BTC": "BTC",
    "Bitcoin": "BTC",
    "ETH": "ETH",
    "Ethereum": "ETH",
}


def detect_asset(question: str) -> str | None:
    for keyword, asset in _ASSET_KEYWORDS.items():
        if keyword.lower() in question.lower():
            return asset
    return None


def is_price_prediction(question: str) -> bool:
    return any(p.search(question) for p in _PRICE_PATTERNS)


class MarketScanner:
    def filter(self, markets: list) -> list:
        candidates = []
        skipped = {"asset": 0, "type": 0, "liquidity": 0, "volume": 0, "expiry": 0, "spread": 0}

        for m in markets:
            # 1. Asset whitelist
            asset = detect_asset(m.question or "")
            if asset not in config.ALLOWED_ASSETS:
                skipped["asset"] += 1
                continue

            # 2. Must be price prediction
            if not is_price_prediction(m.question or ""):
                skipped["type"] += 1
                continue

            # 3. Liquidity
            if m.liquidity < config.MIN_LIQUIDITY:
                skipped["liquidity"] += 1
                continue

            # 4. Volume
            if m.volume_24h < config.MIN_VOLUME_24H:
                skipped["volume"] += 1
                continue

            # 5. Expiry
            days = self._days_to_expiry(m.end_time)
            if days is None or days > config.MAX_DAYS_TO_EXPIRY or days < 0:
                skipped["expiry"] += 1
                continue

            # 6. Spread
            if m.spread > config.MAX_SPREAD:
                skipped["spread"] += 1
                continue

            score = self._score(m, days)
            candidates.append((score, m))

        candidates.sort(key=lambda x: x[0], reverse=True)
        top = [m for _, m in candidates[: config.TOP_MARKETS_COUNT]]

        logger.info(
            "Scanner: %d total → %d candidates → top %d | skipped: %s",
            len(markets), len(candidates), len(top), skipped,
        )
        return top

    def _days_to_expiry(self, end_time: str) -> float | None:
        try:
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            delta = end - datetime.now(timezone.utc)
            return delta.total_seconds() / 86400
        except Exception:
            return None

    def _score(self, m, days: float) -> float:
        volume_score    = min(m.volume_24h / 5_000, 1.0)
        liquidity_score = min(m.liquidity / 3_000, 1.0)
        urgency_score   = 1.0 - (days / config.MAX_DAYS_TO_EXPIRY)   # near expiry = higher score
        spread_score    = 1.0 - (m.spread / config.MAX_SPREAD)
        return (volume_score + liquidity_score + urgency_score + spread_score) / 4
