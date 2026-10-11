"""Currency exchange rate matrix and order book pricing."""

from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple
from .models import CurrencyQuote


class RateMatrix:
    """Multi-currency exchange rate matrix supporting direct quotes and synthetic cross-rates."""

    def __init__(self):
        # Key: (base, quote)
        self.quotes: Dict[Tuple[str, str], CurrencyQuote] = {}
        self.currencies: Set[str] = set()

    def add_quote(
        self,
        base: str,
        quote: str,
        bid: Decimal,
        ask: Decimal,
    ):
        """Add or update an FX quote for currency pair base/quote."""
        b = base.upper().strip()
        q = quote.upper().strip()

        if bid <= Decimal("0") or ask <= Decimal("0"):
            raise ValueError("Bid and ask rates must be strictly positive")
        if bid > ask:
            raise ValueError(f"Crossed market: Bid {bid} > Ask {ask}")

        self.quotes[(b, q)] = CurrencyQuote(base_currency=b, quote_currency=q, bid=bid, ask=ask)
        self.currencies.add(b)
        self.currencies.add(q)

    def get_conversion_rate(self, from_ccy: str, to_ccy: str) -> Optional[Decimal]:
        """Return the effective rate to convert from_ccy to to_ccy (after spread)."""
        src = from_ccy.upper().strip()
        dst = to_ccy.upper().strip()

        if src == dst:
            return Decimal("1")

        # Case 1: Direct quote where src is base, dst is quote
        # E.g. EUR -> USD: we sell EUR at EUR/USD bid
        if (src, dst) in self.quotes:
            return self.quotes[(src, dst)].bid

        # Case 2: Inverse quote where dst is base, src is quote
        # E.g. USD -> EUR: we buy EUR at EUR/USD ask -> rate is 1 / ask
        if (dst, src) in self.quotes:
            ask_rate = self.quotes[(dst, src)].ask
            return Decimal("1") / ask_rate

        return None

    def get_quote(self, base: str, quote: str) -> Optional[CurrencyQuote]:
        b = base.upper().strip()
        q = quote.upper().strip()
        return self.quotes.get((b, q))

    def get_all_currencies(self) -> List[str]:
        return sorted(list(self.currencies))

    @classmethod
    def load_sample_market(cls) -> "RateMatrix":
        """Load standard interbank FX and Bitcoin spot quotes with realistic spreads."""
        matrix = cls()
        matrix.add_quote("EUR", "USD", Decimal("1.0850"), Decimal("1.0852"))
        matrix.add_quote("GBP", "USD", Decimal("1.2948"), Decimal("1.2950"))
        matrix.add_quote("USD", "JPY", Decimal("152.20"), Decimal("152.24"))
        matrix.add_quote("USD", "CHF", Decimal("0.8940"), Decimal("0.8943"))
        matrix.add_quote("USD", "CAD", Decimal("1.3780"), Decimal("1.3784"))
        matrix.add_quote("AUD", "USD", Decimal("0.6650"), Decimal("0.6653"))
        matrix.add_quote("EUR", "GBP", Decimal("0.8378"), Decimal("0.8381"))
        matrix.add_quote("BTC", "USD", Decimal("68500.00"), Decimal("68520.00"))
        matrix.add_quote("EUR", "JPY", Decimal("165.12"), Decimal("165.18"))
        return matrix
