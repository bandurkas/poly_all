"""
MarketCollector — fetches all active Polymarket markets via Gamma API.

Sources:
  - Gamma API (no auth): market metadata, prices, volume, liquidity
  - BTCPriceFeed: current BTC spot price + volatility

For each market, builds a MarketSnapshot with:
  - Standard fields (prices, spread, liquidity, volume)
  - extra dict populated with data needed by probability models:
      current_price, target_price, direction, hours_to_expiry,
      annualized_volatility (for price_prediction markets)

Pagination: Gamma API returns up to 500 markets per page.
We fetch pages until no next_cursor is returned.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import aiohttp

import config
from collector import target_parser
from collector.price_feed import BTCPriceFeed
from scanner.market_scanner import detect_asset, is_price_prediction

logger = logging.getLogger(__name__)

GAMMA_URL    = "https://gamma-api.polymarket.com/markets"
PAGE_LIMIT   = 500
FETCH_PARAMS = {
    "active": "true",
    "closed": "false",
    "limit":  PAGE_LIMIT,
}


@dataclass
class MarketSnapshot:
    market_id: str
    condition_id: str
    question: str
    market_type: str            # "price_prediction" | "event_outcome" | "unknown"
    end_time: str               # ISO string
    liquidity: float
    volume_24h: float
    yes_price: float
    no_price: float
    spread: float
    best_bid: float
    best_ask: float
    last_trade_price: Optional[float] = None
    yes_token_id: Optional[str] = None
    no_token_id: Optional[str] = None
    # Populated for price_prediction markets — used by probability models
    extra: dict = field(default_factory=dict)


class MarketCollector:
    def __init__(self):
        self._markets: dict[str, MarketSnapshot] = {}
        self._price_feed = BTCPriceFeed()
        self._running = False
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        self._running = True
        self._session = aiohttp.ClientSession()
        logger.info("MarketCollector starting")
        try:
            await asyncio.gather(
                self._price_feed.start(),
                self._poll_markets(),
            )
        finally:
            await self._session.close()

    def stop(self):
        self._running = False
        self._price_feed.stop()

    async def get_markets(self) -> list[MarketSnapshot]:
        return list(self._markets.values())

    # ── Polling loop ──────────────────────────────────────────────────────────

    async def _poll_markets(self):
        while self._running:
            try:
                await self._fetch_all_markets()
                logger.info("MarketCollector: %d markets cached", len(self._markets))
            except Exception as e:
                logger.error("Poll error: %s", e)
            await asyncio.sleep(config.PRICE_POLL_INTERVAL)

    # ── Gamma API fetch (paginated) ───────────────────────────────────────────

    async def _fetch_all_markets(self):
        raw_markets = []
        params = {**FETCH_PARAMS}
        next_cursor = None

        while True:
            if next_cursor:
                params["next_cursor"] = next_cursor

            try:
                async with self._session.get(GAMMA_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
            except Exception as e:
                logger.error("Gamma API error: %s", e)
                break

            # Gamma returns either a list or {"data": [...], "next_cursor": "..."}
            if isinstance(data, list):
                raw_markets.extend(data)
                break
            else:
                raw_markets.extend(data.get("data", []))
                next_cursor = data.get("next_cursor")
                if not next_cursor:
                    break

        logger.debug("Fetched %d raw markets from Gamma", len(raw_markets))

        for raw in raw_markets:
            snapshot = self._parse(raw)
            if snapshot:
                self._markets[snapshot.condition_id] = snapshot

    # ── Market parsing ────────────────────────────────────────────────────────

    def _parse(self, raw: dict) -> Optional[MarketSnapshot]:
        condition_id = raw.get("conditionId", "")
        question     = raw.get("question", "")
        end_time     = raw.get("endDate", "") or raw.get("end_date", "")

        if not condition_id or not question or not end_time:
            return None

        # Token IDs
        clob_ids = raw.get("clobTokenIds", [])
        if isinstance(clob_ids, str):
            try:
                clob_ids = json.loads(clob_ids)
            except json.JSONDecodeError:
                clob_ids = []

        yes_token = clob_ids[0] if len(clob_ids) > 0 else None
        no_token  = clob_ids[1] if len(clob_ids) > 1 else None

        # Prices
        outcome_prices = raw.get("outcomePrices", ["0.5", "0.5"])
        try:
            yes_price = float(outcome_prices[0])
            no_price  = float(outcome_prices[1])
        except (IndexError, ValueError, TypeError):
            yes_price, no_price = 0.5, 0.5

        # Spread: how far from the fair 1.0 sum
        spread = abs(1.0 - yes_price - no_price)

        # Volume & liquidity
        volume   = float(raw.get("volumeNum") or raw.get("volume") or 0)
        liquidity = float(raw.get("liquidityNum") or raw.get("liquidity") or 0)

        # Market type classification
        asset = detect_asset(question)
        market_type = "price_prediction" if (asset and is_price_prediction(question)) else "event_outcome"

        # Build extra for probability models
        extra = self._build_extra(question, end_time, market_type)

        return MarketSnapshot(
            market_id=raw.get("id", condition_id),
            condition_id=condition_id,
            question=question,
            market_type=market_type,
            end_time=end_time,
            liquidity=liquidity,
            volume_24h=volume,
            yes_price=yes_price,
            no_price=no_price,
            spread=spread,
            best_bid=yes_price,   # approximation — real orderbook via CLOB WS later
            best_ask=yes_price + spread,
            yes_token_id=yes_token,
            no_token_id=no_token,
            extra=extra,
        )

    def _build_extra(self, question: str, end_time: str, market_type: str) -> dict:
        extra: dict = {}

        # Hours to expiry
        try:
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            hours = (end - datetime.now(timezone.utc)).total_seconds() / 3600
            extra["hours_to_expiry"] = max(hours, 0.0)
        except Exception:
            pass

        if market_type != "price_prediction":
            return extra

        # BTC spot price
        btc_price = self._price_feed.current_price
        if btc_price:
            extra["current_price"] = btc_price

        # Annualised volatility from candles
        vol = self._price_feed.annualized_volatility()
        if vol:
            extra["annualized_volatility"] = vol

        # Target price + direction from question text
        target, direction = target_parser.parse(question)
        if target:
            extra["target_price"] = target
        if direction:
            extra["direction"] = direction

        return extra
