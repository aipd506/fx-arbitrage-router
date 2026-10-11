"""Command Line Interface for FX Arbitrage Router (fxrouter)."""

import argparse
import sys
from decimal import Decimal
from typing import List, Optional
from .models import RoutingPath, ArbitrageOpportunity
from .rates import RateMatrix
from .arbitrage import ArbitrageEngine
from .router import FXRouter


def build_matrix(quotes_args: Optional[List[str]]) -> RateMatrix:
    matrix = RateMatrix.load_sample_market()
    if quotes_args:
        for q_str in quotes_args:
            # Format: EUR/USD=1.0850:1.0852
            try:
                pair, rates = q_str.split("=")
                base, quote = pair.split("/")
                bid_str, ask_str = rates.split(":")
                matrix.add_quote(base, quote, Decimal(bid_str), Decimal(ask_str))
            except Exception as e:
                sys.stderr.write(f"Warning: Failed to parse quote '{q_str}': {e}\n")
    return matrix


def handle_matrix(args: argparse.Namespace) -> int:
    matrix = build_matrix(args.quote)
    print("================================================================================")
    print("                      FOREIGN EXCHANGE SPOT RATE MATRIX                         ")
    print("================================================================================")
    print(f"{'PAIR':<12} | {'BID':>12} | {'ASK':>12} | {'MID':>12} | {'SPREAD (bps)':>14}")
    print("-------------+--------------+--------------+--------------+---------------------")
    for (base, quote), q in sorted(matrix.quotes.items()):
        pair_str = f"{base}/{quote}"
        print(f"{pair_str:<12} | {q.bid:>12.4f} | {q.ask:>12.4f} | {q.mid:>12.4f} | {q.spread_bps:>14.2f}")
    print("================================================================================")
    print(f"Supported Currencies ({len(matrix.currencies)}): {', '.join(matrix.get_all_currencies())}\n")
    return 0


def handle_arbitrage(args: argparse.Namespace) -> int:
    matrix = build_matrix(args.quote)
    fee_rate = Decimal(str(args.fees_bps)) / Decimal("10000")
    engine = ArbitrageEngine(matrix, fee_rate=fee_rate)

    print("================================================================================")
    print(f"                   FX ARBITRAGE SCANNER (Fee: {args.fees_bps} bps/leg)          ")
    print("================================================================================")

    if args.method == "bellman":
        opp = engine.detect_negative_cycle_bellman_ford()
        opportunities = [opp] if opp else []
    elif args.method == "all":
        opportunities = engine.scan_all_cycles(max_depth=args.max_legs)
    else:
        # Default: triangular
        opportunities = engine.scan_triangular()

    if not opportunities:
        print("No profitable arbitrage cycles detected at current pricing and fee levels.")
        print("Market is currently in triangular and cycle parity.\n")
        return 0

    print(f"Detected {len(opportunities)} profitable arbitrage cycle(s):\n")
    for idx, opp in enumerate(opportunities, start=1):
        print(f"--- Opportunity #{idx} ---")
        print(opp.summary())
        print()
    return 0


def handle_route(args: argparse.Namespace) -> int:
    matrix = build_matrix(args.quote)
    fee_rate = Decimal(str(args.fees_bps)) / Decimal("10000")
    router = FXRouter(matrix, default_fee_rate=fee_rate)

    amount = Decimal(str(args.amount))
    res = router.find_best_route(
        source=args.source,
        target=args.target,
        amount=amount,
        max_legs=args.max_legs,
        fee_rate=fee_rate,
    )
    if not res:
        sys.stderr.write(f"Error: No conversion route found from {args.source.upper()} to {args.target.upper()}.\n")
        return 1

    print("================================================================================")
    print(f"              OPTIMAL FX CONVERSION ROUTE: {args.source.upper()} -> {args.target.upper()} ")
    print("================================================================================")
    print(res.summary())
    print("================================================================================\n")
    return 0


def handle_convert(args: argparse.Namespace) -> int:
    matrix = build_matrix(args.quote)
    fee_rate = Decimal(str(args.fees_bps)) / Decimal("10000")
    router = FXRouter(matrix, default_fee_rate=fee_rate)

    amount = Decimal(str(args.amount))
    via = args.via.split(",") if args.via else None

    try:
        res = router.convert(
            source=args.source,
            target=args.target,
            amount=amount,
            via=via,
            fee_rate=fee_rate,
        )
    except Exception as e:
        sys.stderr.write(f"Conversion Error: {e}\n")
        return 1

    print("================================================================================")
    print(f"                       FX CONVERSION EXECUTION RECEIPT                          ")
    print("================================================================================")
    print(res.summary())
    print("================================================================================\n")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fxrouter",
        description="Foreign Exchange (FX) Cross-Currency Arbitrage Scanner and Multi-Leg Routing Engine",
    )
    parser.add_argument(
        "--quote",
        action="append",
        help="Custom quote in format BASE/QUOTE=BID:ASK (e.g. EUR/USD=1.0850:1.0852)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: matrix
    subparsers.add_parser("matrix", help="Display current spot rate matrix and bid/ask spreads")

    # Subcommand: arbitrage
    p_arb = subparsers.add_parser("arbitrage", help="Scan currency graph for arbitrage cycles")
    p_arb.add_argument("--fees-bps", type=float, default=5.0, help="Per-leg fee/slippage in basis points (default: 5 bps)")
    p_arb.add_argument("--method", choices=["triangular", "bellman", "all"], default="triangular", help="Arbitrage detection algorithm")
    p_arb.add_argument("--max-legs", type=int, default=4, help="Maximum legs in cycle scan (for method 'all')")

    # Subcommand: route
    p_route = subparsers.add_parser("route", help="Find optimal conversion route between two currencies")
    p_route.add_argument("source", help="Source currency code (e.g. EUR, GBP, BTC)")
    p_route.add_argument("target", help="Target currency code (e.g. JPY, USD, CHF)")
    p_route.add_argument("--amount", type=float, default=1000.0, help="Conversion principal amount (default: 1000.0)")
    p_route.add_argument("--fees-bps", type=float, default=5.0, help="Per-leg fee in bps")
    p_route.add_argument("--max-legs", type=int, default=4, help="Maximum allowed legs in route")

    # Subcommand: convert
    p_conv = subparsers.add_parser("convert", help="Execute conversion step simulation")
    p_conv.add_argument("source", help="Source currency")
    p_conv.add_argument("target", help="Target currency")
    p_conv.add_argument("amount", type=float, help="Amount to convert")
    p_conv.add_argument("--via", help="Comma-separated intermediate hops (e.g. USD,EUR)")
    p_conv.add_argument("--fees-bps", type=float, default=5.0, help="Per-leg fee in bps")

    args = parser.parse_args(argv)

    if args.command == "matrix":
        return handle_matrix(args)
    elif args.command == "arbitrage":
        return handle_arbitrage(args)
    elif args.command == "route":
        return handle_route(args)
    elif args.command == "convert":
        return handle_convert(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
