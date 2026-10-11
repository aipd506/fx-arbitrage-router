"""Unit tests for fxrouter CLI commands."""

from fx_arbitrage_router.cli import main


def test_cli_matrix(capsys):
    ret = main(["matrix"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "EUR/USD" in captured.out
    assert "SPREAD (bps)" in captured.out


def test_cli_arbitrage(capsys):
    ret = main(["arbitrage", "--fees-bps", "5.0", "--method", "triangular"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "FX ARBITRAGE SCANNER" in captured.out


def test_cli_arbitrage_with_synthetic_quote(capsys):
    # Pass quotes that trigger arbitrage
    ret = main([
        "--quote", "EUR/USD=1.2000:1.2001",
        "--quote", "GBP/USD=1.5000:1.5001",
        "--quote", "EUR/GBP=0.8500:0.8501",
        "arbitrage",
        "--fees-bps", "1.0",
        "--method", "bellman",
    ])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Arbitrage Cycle" in captured.out or "profitable" in captured.out


def test_cli_route(capsys):
    ret = main(["route", "AUD", "JPY", "--amount", "5000", "--fees-bps", "2.0"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "OPTIMAL FX CONVERSION ROUTE" in captured.out
    assert "AUD -> USD -> JPY" in captured.out


def test_cli_convert(capsys):
    ret = main(["convert", "EUR", "JPY", "1000", "--via", "USD", "--fees-bps", "3.0"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "FX CONVERSION EXECUTION RECEIPT" in captured.out
