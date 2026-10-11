"""Unit tests for RateMatrix and CurrencyQuote models."""

from decimal import Decimal
import pytest
from fx_arbitrage_router.models import CurrencyQuote
from fx_arbitrage_router.rates import RateMatrix


def test_currency_quote_properties():
    q = CurrencyQuote(
        base_currency="EUR",
        quote_currency="USD",
        bid=Decimal("1.0800"),
        ask=Decimal("1.0804"),
    )
    assert q.mid == Decimal("1.0802")
    assert q.spread == Decimal("0.0004")
    # spread_bps = (0.0004 / 1.0802) * 10000 approx 3.70
    assert abs(q.spread_bps - Decimal("3.7030")) < Decimal("0.01")


def test_rate_matrix_add_and_conversion():
    m = RateMatrix()
    m.add_quote("EUR", "USD", Decimal("1.0800"), Decimal("1.0804"))

    # Direct: EUR -> USD converts at bid (selling EUR for USD)
    eur_usd = m.get_conversion_rate("EUR", "USD")
    assert eur_usd == Decimal("1.0800")

    # Inverse: USD -> EUR converts at 1 / ask (buying EUR with USD)
    usd_eur = m.get_conversion_rate("USD", "EUR")
    assert usd_eur == Decimal("1") / Decimal("1.0804")

    # Self conversion is 1.0
    assert m.get_conversion_rate("USD", "USD") == Decimal("1")
    assert m.get_conversion_rate("EUR", "EUR") == Decimal("1")

    # Non-existent pair
    assert m.get_conversion_rate("EUR", "XYZ") is None


def test_invalid_quotes():
    m = RateMatrix()
    with pytest.raises(ValueError, match="strictly positive"):
        m.add_quote("EUR", "USD", Decimal("-1"), Decimal("1.08"))

    with pytest.raises(ValueError, match="strictly positive"):
        m.add_quote("EUR", "USD", Decimal("1.08"), Decimal("0"))

    with pytest.raises(ValueError, match="Crossed market"):
        m.add_quote("EUR", "USD", Decimal("1.10"), Decimal("1.05"))


def test_sample_market_loader():
    m = RateMatrix.load_sample_market()
    currencies = m.get_all_currencies()
    assert "EUR" in currencies
    assert "USD" in currencies
    assert "GBP" in currencies
    assert "JPY" in currencies
    assert "BTC" in currencies
    assert len(currencies) >= 7
