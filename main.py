"""
poly_all — main entry point.

Orchestrates the full pipeline:
  Collector → Scanner → Probability Engine → Mispricing Detector
  → Risk Manager → Trade Executor → Monitoring
"""

import asyncio
import logging

import config
from collector.market_collector import MarketCollector
from scanner.market_scanner import MarketScanner
from probability.engine import ProbabilityEngine
from detector.mispricing_detector import MispricingDetector
from risk.risk_manager import RiskManager
from executor.trade_executor import TradeExecutor
from monitoring.monitor import Monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


async def run():
    logger.info("Starting poly_all trading system (DRY_RUN=%s)", config.DRY_RUN)

    collector = MarketCollector()
    scanner = MarketScanner()
    prob_engine = ProbabilityEngine()
    detector = MispricingDetector()
    risk_mgr = RiskManager()
    executor = TradeExecutor()
    monitor = Monitor()

    # Start background tasks
    await asyncio.gather(
        collector.start(),
        monitor.start(),
        main_loop(collector, scanner, prob_engine, detector, risk_mgr, executor, monitor),
    )


async def main_loop(collector, scanner, prob_engine, detector, risk_mgr, executor, monitor):
    while True:
        try:
            # 1. Get current snapshot of all markets
            markets = await collector.get_markets()

            # 2. Filter to top candidates
            candidates = scanner.filter(markets)

            for market in candidates:
                # 3. Calculate model probability
                model_prob = await prob_engine.calculate(market)
                if model_prob is None:
                    continue

                # 4. Detect mispricing / calculate edge
                signal = detector.evaluate(market, model_prob)
                if signal is None:
                    continue

                # 5. Risk check + position sizing
                sized = risk_mgr.size(signal)
                if sized is None:
                    continue

                # 6. Execute trade
                result = await executor.execute(sized)

                # 7. Log to monitor
                monitor.record(result)

        except Exception as e:
            logger.exception("Error in main loop: %s", e)

        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run())
