"""
MarketCollector — fetches and caches all Polymarket markets.

- REST polling for prices and volume
- WebSocket streaming for orderbook (top N markets by volume)
- Stores state in Redis
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

import config

logger = logging.getLogger(__name__)


@dataclass
class MarketSnapshot:
    market_id: str
    condition_id: str
    question: str
    market_type: str            # "price_prediction" | "event_outcome" | "unknown"
    end_time: str
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
    extra: dict = field(default_factory=dict)


class MarketCollector:
    def __init__(self):
        self._markets: dict[str, MarketSnapshot] = {}
        self._running = False

    async def start(self):
        self._running = True
        logger.info("MarketCollector starting")
        await asyncio.gather(
            self._poll_markets(),
            self._ws_orderbook(),
        )

    async def get_markets(self) -> list[MarketSnapshot]:
        return list(self._markets.values())

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _poll_markets(self):
        """Poll all active markets via REST every PRICE_POLL_INTERVAL seconds."""
        while self._running:
            try:
                await self._fetch_all_markets()
            except Exception as e:
                logger.error("Poll error: %s", e)
            await asyncio.sleep(config.PRICE_POLL_INTERVAL)

    async def _fetch_all_markets(self):
        # TODO: implement using py-clob-client
        # from py_clob_client.client import ClobClient
        # client = ClobClient(...)
        # markets = client.get_markets()
        # for m in markets: self._markets[m.condition_id] = self._parse(m)
        logger.debug("_fetch_all_markets: not yet implemented")

    async def _ws_orderbook(self):
        """Stream orderbook updates via WebSocket for top markets."""
        # TODO: implement WebSocket streaming
        # Subscribe to top WS_ORDERBOOK_TOP_N markets by volume
        while self._running:
            await asyncio.sleep(60)
