"""
TradeExecutor — places orders on Polymarket CLOB.

In DRY_RUN mode: logs the intended trade, does not place real orders.
In live mode: places limit orders, waits for fill, adjusts if needed.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import config

logger = logging.getLogger(__name__)


@dataclass
class TradeResult:
    market_id: str
    direction: str
    bet_amount: float
    actual_amount: Optional[float]
    actual_price: Optional[float]
    order_id: Optional[str]
    dry_run: bool
    success: bool
    error: Optional[str] = None


class TradeExecutor:
    def __init__(self):
        self._client = None  # py-clob-client instance

    async def execute(self, sized_signal) -> TradeResult:
        signal = sized_signal.signal
        bet = sized_signal.bet_amount

        if config.DRY_RUN:
            logger.info(
                "[DRY RUN] Would buy %s on %s for $%.2f (edge=%.3f)",
                signal.direction, signal.market_id, bet, signal.edge,
            )
            return TradeResult(
                market_id=signal.market_id,
                direction=signal.direction,
                bet_amount=bet,
                actual_amount=None,
                actual_price=None,
                order_id=None,
                dry_run=True,
                success=True,
            )

        try:
            result = await self._place_order(signal, bet)
            return result
        except Exception as e:
            logger.error("Execute error for %s: %s", signal.market_id, e)
            return TradeResult(
                market_id=signal.market_id,
                direction=signal.direction,
                bet_amount=bet,
                actual_amount=None,
                actual_price=None,
                order_id=None,
                dry_run=False,
                success=False,
                error=str(e),
            )

    async def _place_order(self, signal, bet: float) -> TradeResult:
        # TODO: implement using py-clob-client
        # market = signal.market
        # token_id = market.yes_token_id if signal.direction == "YES" else market.no_token_id
        # resp = self._client.create_market_order(token_id=token_id, amount=bet)
        # ... parse fill
        raise NotImplementedError("Live order placement not yet implemented")

    def _init_client(self):
        # TODO: initialise ClobClient with credentials from config
        pass
