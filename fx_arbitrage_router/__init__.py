"""Foreign Exchange (FX) Cross-Currency Arbitrage Scanner and Multi-Leg Routing Engine."""

from .models import CurrencyQuote, ConversionStep, RoutingPath, ArbitrageOpportunity
from .rates import RateMatrix
from .arbitrage import ArbitrageEngine
from .router import FXRouter

__version__ = "0.1.0"
__all__ = [
    "CurrencyQuote",
    "ConversionStep",
    "RoutingPath",
    "ArbitrageOpportunity",
    "RateMatrix",
    "ArbitrageEngine",
    "FXRouter",
]
