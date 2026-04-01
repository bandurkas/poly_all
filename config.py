"""
Global configuration for poly_all trading system.
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
WS_ORDERBOOK_TOP_N = 200        # top N markets by volume get WebSocket orderbook

# ─── Market Scanner Filters ──────────────────────────────────────────────────
MIN_LIQUIDITY = 500             # USD
MIN_VOLUME_24H = 1000           # USD
MAX_DAYS_TO_EXPIRY = 7          # days
TOP_MARKETS_COUNT = 20

# ─── Probability Engine ──────────────────────────────────────────────────────
MONTE_CARLO_SIMULATIONS = 10_000

# Model weights for ensemble (per market type)
MODEL_WEIGHTS = {
    "price_prediction": {
        "market_implied": 0.20,
        "historical":     0.30,
        "volatility":     0.30,
        "momentum":       0.20,
    },
    "event_outcome": {
        "market_implied": 0.70,
        "momentum":       0.30,
        "historical":     0.00,
        "volatility":     0.00,
    },
    "unknown": {
        "market_implied": 1.00,
        "historical":     0.00,
        "volatility":     0.00,
        "momentum":       0.00,
    },
}

# ─── Mispricing Detector ─────────────────────────────────────────────────────
MIN_EDGE = 0.08                 # 8% minimum edge to consider a trade
MAX_SPREAD = 0.05               # 5% max spread

# ─── Risk Manager ────────────────────────────────────────────────────────────
TOTAL_CAPITAL = 100.0           # USD — update to actual balance
MAX_POSITION_PCT = 0.05         # 5% of capital per trade
MAX_TOTAL_EXPOSURE_PCT = 0.20   # 20% total open exposure
KELLY_FRACTION = 0.25           # fractional Kelly multiplier (conservative)
MIN_BET = 1.10                  # USD minimum order size on Polymarket

# ─── Trade Executor ──────────────────────────────────────────────────────────
DRY_RUN = True                  # set False to enable live trading
ORDER_TIMEOUT = 30              # seconds to wait for limit order fill

# ─── Monitoring ──────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = ""             # fill in
TELEGRAM_CHAT_ID = ""           # fill in
DASHBOARD_PORT = 8000
