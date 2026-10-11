"""Unit tests for FXRouter."""

from decimal import Decimal
import pytest
from fx_arbitrage_router.rates import RateMatrix
from fx_arbitrage_router.router import FXRouter


def test_router_same_currency():
    m = RateMatrix.load_sample_market()
    router = FXRouter(m)
    res = router.find_best_route("USD", "USD", amount=Decimal("1000"))
    assert res is not None
    assert res.final_amount == Decimal("1000")
    assert res.overall_effective_rate == Decimal("1")


def test_router_multi_leg_path():
    m = RateMatrix.load_sample_market()
    router = FXRouter(m, default_fee_rate=Decimal("0.0001"))
    # AUD -> JPY does not have a direct quote in sample market (AUD/USD exists, USD/JPY exists)
    res = router.find_best_route("AUD", "JPY", amount=Decimal("1000"))
    assert res is not None
    assert len(res.steps) == 2
    # AUD -> USD -> JPY
    assert res.steps[0].from_currency == "AUD"
    assert res.steps[0].to_currency == "USD"
    assert res.steps[1].from_currency == "USD"
    assert res.steps[1].to_currency == "JPY"
    assert res.final_amount > Decimal("50000")


def test_router_convert_explicit_via():
    m = RateMatrix.load_sample_market()
    router = FXRouter(m, default_fee_rate=Decimal("0.0002"))
    # Convert EUR to JPY via USD
    res = router.convert("EUR", "JPY", Decimal("1000"), via=["USD"])
    assert len(res.steps) == 2
    assert res.steps[0].to_currency == "USD"
    assert res.steps[1].to_currency == "JPY"
    assert res.final_amount > Decimal("100000")


def test_router_unknown_currency():
    m = RateMatrix.load_sample_market()
    router = FXRouter(m)
    res = router.find_best_route("EUR", "UNKNOWN", amount=Decimal("1000"))
    assert res is None

    with pytest.raises(ValueError, match="No route found"):
        router.convert("EUR", "UNKNOWN", Decimal("1000"))
