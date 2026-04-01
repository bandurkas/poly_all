"""
Global configuration for poly_all trading system.

v1: BTC price prediction markets only.
"""

# ─── VPS / Infra ────────────────────────────────────────────────────────────
REDIS_URL = "redis://localhost:6379"
POSTGRES_URL = "postgresql://poly:poly@localhost:5432/poly_all"

# ─── Polymarket Credentials ──────────────────────────────────────────────────
POLY_API_KEY = "019d45d8-233d-7283-ab26-594d3a8ae535"
POLY_API_SECRET = ""
POLY_API_PASSPHRASE = ""
POLY_PRIVATE_KEY = "0xab0b9144dc16d0b2fa6c74bef797990cb5154ed8a6ae98b9f880138ab034b624"
FUNDER_ADDRESS = "0x3a1F68Bf518823A506E6BE1b390899a872921337"
SIGNATURE_TYPE = 1  # gasless/proxy mode

# ─── Data Collection ─────────────────────────────────────────────────────────
PRICE_POLL_INTERVAL = 3         # seconds
VOLUME_POLL_INTERVAL = 10       # seconds
WS_ORDERBOOK_TOP_N = 50         # v1: only crypto price markets, smaller set

# ─── Version / Roadmap ───────────────────────────────────────────────────────
# v1: BTC price markets only
# v2: add ETH + macro (rates, CPI)
# v3: politics / news / sports

# ─── Market Scanner Filters (v1: small capital) ──────────────────────────────
ALLOWED_ASSETS = ["BTC"]        # v1: BTC only. add "ETH" for v2
MIN_LIQUIDITY = 300             # USD
MIN_VOLUME_24H = 500            # USD
MAX_DAYS_TO_EXPIRY = 7          # days
TOP_MARKETS_COUNT = 10

# ─── Probability Engine ──────────────────────────────────────────────────────
MONTE_CARLO_SIMULATIONS = 10_000

# v1: volatility model only (Monte Carlo). historical/momentum disabled until data accumulates.
MODEL_WEIGHTS = {
    "price_prediction": {
        "market_implied": 0.30,
        "volatility":     0.70,
        "historical":     0.00,  # enable in v2 once DB has 30+ samples
        "momentum":       0.00,  # enable in v2
    },
    "event_outcome": {
        "market_implied": 1.00,
        "volatility":     0.00,
        "historical":     0.00,
        "momentum":       0.00,
    },
    "unknown": {
        "market_implied": 1.00,
        "volatility":     0.00,
        "historical":     0.00,
        "momentum":       0.00,
    },
}

# ─── Mispricing Detector ─────────────────────────────────────────────────────
# Small capital → need larger edge to offset spread and slippage
MIN_EDGE = 0.12                 # 12% minimum edge (raise to 0.15 if too many trades)
MAX_SPREAD = 0.05               # 5% max spread

# ─── Risk Manager ────────────────────────────────────────────────────────────
TOTAL_CAPITAL = 50.0            # USD — update to actual balance
MAX_POSITION_PCT = 0.06         # 6% of capital per trade (~$3 on $50)
MAX_TOTAL_EXPOSURE_PCT = 0.20   # 20% total open = ~$10 on $50
KELLY_FRACTION = 0.25           # fractional Kelly (conservative)
MIN_BET = 1.10                  # USD minimum order size on Polymarket
MAX_BET = 5.0                   # USD hard cap per trade for v1

# ─── Trade Executor ──────────────────────────────────────────────────────────
DRY_RUN = True                  # paper trading — set False only after validation
ORDER_TIMEOUT = 30              # seconds to wait for limit order fill

# ─── Monitoring ──────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = ""             # fill in
TELEGRAM_CHAT_ID = ""           # fill in
DASHBOARD_PORT = 8000

# ─── Graduation Criteria (paper → live) ──────────────────────────────────────
# Switch DRY_RUN = False only when after 1–2 weeks paper trading:
#   win_rate > 0.55
#   avg_edge > 0.10
#   drawdown < 15% of capital
