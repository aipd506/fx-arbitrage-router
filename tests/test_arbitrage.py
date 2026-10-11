"""Unit tests for ArbitrageEngine and negative cycle detection."""

from decimal import Decimal
from fx_arbitrage_router.rates import RateMatrix
from fx_arbitrage_router.arbitrage import ArbitrageEngine


def test_market_without_arbitrage():
    # In efficient markets, spreads make loops < 1
    m = RateMatrix.load_sample_market()
    engine = ArbitrageEngine(m, fee_rate=Decimal("0.0010"))
    opps = engine.scan_triangular()
    # Sample market with 10 bps fee should have no naive arbitrage
    assert len(opps) == 0


def test_triangular_arbitrage_detection():
    m = RateMatrix()
    # Inject synthetic mispricing:
    # EUR/USD = 1.2000
    # GBP/USD = 1.5000  (meaning EUR/GBP theoretical = 1.2 / 1.5 = 0.8000)
    # Suppose EUR/GBP is misquoted at 0.8500:
    # 1. Start with 1,000 EUR
    # 2. Sell EUR for GBP at 0.8500 -> 850 GBP
    # 3. Sell GBP for USD at 1.5000 -> 1,275 USD
    # 4. Buy EUR with USD at 1.2000 -> 1,275 / 1.2000 = 1,062.50 EUR (+6.25% profit!)
    m.add_quote("EUR", "USD", Decimal("1.2000"), Decimal("1.2001"))
    m.add_quote("GBP", "USD", Decimal("1.5000"), Decimal("1.5001"))
    m.add_quote("EUR", "GBP", Decimal("0.8500"), Decimal("0.8501"))

    engine = ArbitrageEngine(m, fee_rate=Decimal("0.0005"))
    opps = engine.scan_triangular()
    assert len(opps) >= 1
    best = opps[0]
    assert best.profit_pct > Decimal("0")
    assert best.net_multiplier > Decimal("1.0")
    assert len(best.execution_steps) == 3


def test_bellman_ford_arbitrage_detection():
    m = RateMatrix()
    m.add_quote("EUR", "USD", Decimal("1.2000"), Decimal("1.2001"))
    m.add_quote("GBP", "USD", Decimal("1.5000"), Decimal("1.5001"))
    m.add_quote("EUR", "GBP", Decimal("0.8500"), Decimal("0.8501"))

    engine = ArbitrageEngine(m, fee_rate=Decimal("0.0005"))
    opp = engine.detect_negative_cycle_bellman_ford()
    assert opp is not None
    assert opp.net_multiplier > Decimal("1.0")
    assert opp.profit_pct > Decimal("0")


def test_scan_all_cycles():
    m = RateMatrix()
    m.add_quote("EUR", "USD", Decimal("1.2000"), Decimal("1.2001"))
    m.add_quote("GBP", "USD", Decimal("1.5000"), Decimal("1.5001"))
    m.add_quote("EUR", "GBP", Decimal("0.8500"), Decimal("0.8501"))

    engine = ArbitrageEngine(m, fee_rate=Decimal("0.0005"))
    all_opps = engine.scan_all_cycles(max_depth=4)
    assert len(all_opps) >= 1
    assert all_opps[0].profit_pct > Decimal("0")
