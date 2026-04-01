"""
Monitor — tracks performance metrics and sends Telegram notifications.

Metrics tracked:
  - Total trades, wins, losses
  - Win rate
  - Average edge at entry
  - Total PnL, drawdown
  - Open positions
"""

import logging
from dataclasses import dataclass, field

import config

logger = logging.getLogger(__name__)


@dataclass
class Stats:
    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    peak_pnl: float = 0.0
    total_edge: float = 0.0

    @property
    def win_rate(self) -> float:
        closed = self.wins + self.losses
        return self.wins / closed if closed > 0 else 0.0

    @property
    def avg_edge(self) -> float:
        return self.total_edge / self.trades if self.trades > 0 else 0.0

    @property
    def drawdown(self) -> float:
        return self.peak_pnl - self.total_pnl


class Monitor:
    def __init__(self):
        self.stats = Stats()
        self._open_positions: dict = {}

    async def start(self):
        logger.info("Monitor started")
        # TODO: start FastAPI dashboard on config.DASHBOARD_PORT

    def record(self, result):
        if result is None:
            return
        self.stats.trades += 1
        if hasattr(result, "edge"):
            self.stats.total_edge += result.edge
        logger.info("Trade recorded: %s", result)

    def record_outcome(self, market_id: str, pnl: float):
        self.stats.total_pnl += pnl
        self.stats.peak_pnl = max(self.stats.peak_pnl, self.stats.total_pnl)
        if pnl > 0:
            self.stats.wins += 1
        else:
            self.stats.losses += 1
        self._notify_outcome(market_id, pnl)

    def print_stats(self):
        s = self.stats
        logger.info(
            "Stats | trades=%d win_rate=%.1f%% avg_edge=%.3f pnl=$%.2f drawdown=$%.2f",
            s.trades, s.win_rate * 100, s.avg_edge, s.total_pnl, s.drawdown,
        )

    def _notify_outcome(self, market_id: str, pnl: float):
        # TODO: send Telegram message
        emoji = "✅" if pnl > 0 else "❌"
        msg = f"{emoji} {'WIN' if pnl > 0 else 'LOSS'} | {market_id} | PnL: ${pnl:+.2f}"
        logger.info("Telegram (stub): %s", msg)
