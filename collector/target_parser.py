"""
TargetParser — extracts target price and direction from a market question.

Handles patterns like:
  "Will BTC be above $80,000 on April 1?"
  "Bitcoin above $85,000 by Friday?"
  "BTC > $90k end of day?"
  "Will BTC close below $75,000?"
  "Bitcoin to hit $100k?"
  "BTC/USD above 85000"
  "Will Bitcoin stay above $80k?"

Returns: (target_price: float, direction: "above" | "below") or (None, None)
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Price extraction ──────────────────────────────────────────────────────────
# Matches: $80,000  $85k  $90.5k  85000  80,000
_PRICE_RE = re.compile(
    r"\$?([\d,]+(?:\.\d+)?)\s*(k|K|thousand)?",
)

# ── Direction keywords ────────────────────────────────────────────────────────
_ABOVE_WORDS = re.compile(
    r"\b(above|over|higher than|exceed|hit|reach|break|surpass|>|at least)\b",
    re.IGNORECASE,
)
_BELOW_WORDS = re.compile(
    r"\b(below|under|lower than|drop below|fall below|<|at most)\b",
    re.IGNORECASE,
)

# ── Reasonable BTC price range (sanity check) ─────────────────────────────────
_BTC_MIN = 1_000
_BTC_MAX = 1_000_000


def parse(question: str) -> tuple[Optional[float], Optional[str]]:
    """
    Returns (target_price, direction) or (None, None) if not parseable.
    direction: "above" | "below"
    """
    if not question:
        return None, None

    target = _extract_price(question)
    if target is None:
        return None, None

    direction = _extract_direction(question)
    if direction is None:
        return None, None

    logger.debug("Parsed '%s' → target=$%.2f dir=%s", question[:60], target, direction)
    return target, direction


def _extract_price(text: str) -> Optional[float]:
    """Find the most likely target price in the question."""
    candidates = []
    for m in _PRICE_RE.finditer(text):
        raw = m.group(1).replace(",", "")
        try:
            value = float(raw)
        except ValueError:
            continue

        multiplier = m.group(2)
        if multiplier and multiplier.lower() in ("k", "thousand"):
            value *= 1000

        if _BTC_MIN <= value <= _BTC_MAX:
            candidates.append(value)

    if not candidates:
        return None

    # If multiple matches, prefer the largest (usually the target price, not e.g. volume)
    # Exception: if there's clearly one dominant price, use that
    if len(candidates) == 1:
        return candidates[0]

    # Filter out very small numbers that are likely percentages or counts
    valid = [v for v in candidates if v >= 10_000]
    return valid[0] if valid else candidates[-1]


def _extract_direction(text: str) -> Optional[str]:
    has_above = bool(_ABOVE_WORDS.search(text))
    has_below = bool(_BELOW_WORDS.search(text))

    if has_above and not has_below:
        return "above"
    if has_below and not has_above:
        return "below"
    if has_above and has_below:
        # Ambiguous: look at word order — first directional word wins
        above_pos = _ABOVE_WORDS.search(text).start()
        below_pos = _BELOW_WORDS.search(text).start()
        return "above" if above_pos < below_pos else "below"

    return None
