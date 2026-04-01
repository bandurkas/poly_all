"""
BTC price feed: Binance + Coinbase + Chainlink.

Returns median of available sources as trading price.
Builds 1-minute candles for volatility calculation.
Chainlink is used for reference only (slow RPC updates).
"""

import asyncio
import json
import logging
import math
import time
import urllib.request
from collections import deque
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

BINANCE_URL        = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
COINBASE_URL       = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
CHAINLINK_CONTRACT = "0xc907E116054Ad103354f2D350FD2514433D57F6f"
POLYGON_RPC        = "https://1rpc.io/matic"
LATEST_ROUND_DATA  = "0xfeaf968c"

POLL_INTERVAL      = 2.0   # seconds
CANDLE_SECONDS     = 60    # 1-minute candles
MIN_CANDLES_READY  = 3     # minimum candles before feed is "ready"
HISTORY_CANDLES    = 30    # candles kept for volatility calc (~30 min)


@dataclass
class Candle:
    open:  float
    high:  float
    low:   float
    close: float
    ticks: int
    ts:    float   # unix timestamp of candle open


class BTCPriceFeed:
    def __init__(self):
        self.current_price: Optional[float] = None
        self.candles: deque[Candle] = deque(maxlen=HISTORY_CANDLES)
        self._source_prices: dict[str, float] = {}
        self._running = False

        self._cur_open:  Optional[float] = None
        self._cur_high:  float = 0.0
        self._cur_low:   float = float("inf")
        self._cur_ticks: int = 0
        self._cur_start: Optional[float] = None

    async def start(self):
        self._running = True
        logger.info("BTCPriceFeed started")
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                price = await loop.run_in_executor(None, self._fetch_all)
                if price and price > 0:
                    self.current_price = price
                    self._update_candle(price)
            except Exception as e:
                logger.warning("PriceFeed error: %s", e)
            await asyncio.sleep(POLL_INTERVAL)

    def stop(self):
        self._running = False

    @property
    def is_ready(self) -> bool:
        return self.current_price is not None and len(self.candles) >= MIN_CANDLES_READY

    @property
    def chainlink_price(self) -> Optional[float]:
        return self._source_prices.get("chainlink")

    # ── Volatility ────────────────────────────────────────────────────────────

    def annualized_volatility(self, window: int = 20) -> Optional[float]:
        """
        Annualized volatility from log returns of 1-min candles.
        window: number of candles to use (default 20 = 20 minutes).
        """
        candles = list(self.candles)
        if len(candles) < 3:
            return None
        recent = candles[-min(window, len(candles)):]
        log_returns = [
            math.log(recent[i].close / recent[i - 1].close)
            for i in range(1, len(recent))
            if recent[i - 1].close > 0
        ]
        if len(log_returns) < 2:
            return None
        n = len(log_returns)
        mean = sum(log_returns) / n
        variance = sum((r - mean) ** 2 for r in log_returns) / (n - 1)
        std_per_minute = math.sqrt(variance)
        # Annualise: sqrt(365 * 24 * 60) minutes per year
        return std_per_minute * math.sqrt(365 * 24 * 60)

    def atr(self, period: int = 14) -> Optional[float]:
        """Average True Range over last `period` candles (USD)."""
        candles = list(self.candles)
        if len(candles) < 2:
            return None
        recent = candles[-min(period + 1, len(candles)):]
        trs = []
        for i in range(1, len(recent)):
            prev_close = recent[i - 1].close
            tr = max(
                recent[i].high - recent[i].low,
                abs(recent[i].high - prev_close),
                abs(recent[i].low - prev_close),
            )
            trs.append(tr)
        return sum(trs) / len(trs) if trs else None

    # ── Internals ─────────────────────────────────────────────────────────────

    def _fetch_all(self) -> float:
        results: dict[str, float] = {}

        # Binance
        try:
            req = urllib.request.Request(BINANCE_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as r:
                results["binance"] = float(json.loads(r.read())["price"])
        except Exception as e:
            logger.debug("Binance unavailable: %s", e)

        # Coinbase
        try:
            req = urllib.request.Request(COINBASE_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as r:
                results["coinbase"] = float(json.loads(r.read())["data"]["amount"])
        except Exception as e:
            logger.debug("Coinbase unavailable: %s", e)

        # Chainlink (reference only)
        try:
            payload = json.dumps({
                "jsonrpc": "2.0", "method": "eth_call",
                "params": [{"to": CHAINLINK_CONTRACT, "data": LATEST_ROUND_DATA}, "latest"],
                "id": 1,
            }).encode()
            req = urllib.request.Request(
                POLYGON_RPC, data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                result = json.loads(r.read()).get("result", "")
                if result and len(result) >= 130:
                    results["chainlink"] = int(result[2 + 64: 2 + 128], 16) / 1e8
        except Exception as e:
            logger.debug("Chainlink unavailable: %s", e)

        if not results:
            return 0.0

        self._source_prices = results

        exchange = {k: v for k, v in results.items() if k in ("binance", "coinbase")}
        use = exchange if exchange else results
        values = sorted(use.values())
        n = len(values)
        if n == 1:
            price = values[0]
        elif n == 2:
            spread = (values[-1] - values[0]) / values[0]
            price = use.get("binance", values[0]) if spread > 0.02 else (values[0] + values[1]) / 2
        else:
            price = values[n // 2]

        src_str = " | ".join(f"{k}=${v:,.2f}" for k, v in sorted(results.items()))
        logger.debug("BTC prices: %s → trade=$%,.2f", src_str, price)
        return price

    def _update_candle(self, price: float):
        now = time.time()
        bucket = now - (now % CANDLE_SECONDS)

        if self._cur_start is None:
            self._cur_start = bucket

        if bucket > self._cur_start and self._cur_open is not None:
            self.candles.append(Candle(
                open=self._cur_open, high=self._cur_high,
                low=self._cur_low, close=price,
                ticks=self._cur_ticks, ts=self._cur_start,
            ))
            self._cur_start = bucket
            self._cur_open  = price
            self._cur_high  = price
            self._cur_low   = price
            self._cur_ticks = 1
        else:
            if self._cur_open is None:
                self._cur_open = price
            self._cur_high  = max(self._cur_high, price)
            self._cur_low   = min(self._cur_low, price)
            self._cur_ticks += 1
