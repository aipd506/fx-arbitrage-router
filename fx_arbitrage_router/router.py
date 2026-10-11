"""Optimal multi-leg currency routing engine."""

from decimal import Decimal
from typing import List, Optional, Set
from .models import ConversionStep, RoutingPath
from .rates import RateMatrix


class FXRouter:
    """Finds optimal multi-leg currency conversion paths and executes conversion simulations."""

    def __init__(self, matrix: RateMatrix, default_fee_rate: Decimal = Decimal("0.0005")):
        self.matrix = matrix
        self.default_fee_rate = default_fee_rate

    def find_best_route(
        self,
        source: str,
        target: str,
        amount: Decimal = Decimal("1000"),
        max_legs: int = 4,
        fee_rate: Optional[Decimal] = None,
    ) -> Optional[RoutingPath]:
        """
        Find the optimal route from source to target maximizing final amount after fees.
        Enumerates acyclic paths up to max_legs.
        """
        src = source.upper().strip()
        dst = target.upper().strip()
        fee = self.default_fee_rate if fee_rate is None else fee_rate

        if src not in self.matrix.currencies or dst not in self.matrix.currencies:
            return None

        if src == dst:
            step = ConversionStep(
                from_currency=src,
                to_currency=dst,
                rate=Decimal("1"),
                input_amount=amount,
                output_amount=amount,
            )
            return RoutingPath(
                source_currency=src,
                target_currency=dst,
                steps=[step],
                overall_effective_rate=Decimal("1"),
                initial_amount=amount,
                final_amount=amount,
                direct_rate=Decimal("1"),
                improvement_bps=Decimal("0"),
            )

        currencies = self.matrix.get_all_currencies()
        best_path: Optional[List[str]] = None
        best_final_amount = Decimal("-1")

        def dfs(current: str, path: List[str], current_amt: Decimal):
            nonlocal best_path, best_final_amount
            if len(path) > max_legs:
                return

            if current == dst:
                if current_amt > best_final_amount:
                    best_final_amount = current_amt
                    best_path = list(path)
                return

            for nxt in currencies:
                if nxt in path:
                    continue
                rate = self.matrix.get_conversion_rate(current, nxt)
                if rate is None:
                    continue
                # Fee deducted on conversion leg
                leg_amt = current_amt * rate * (Decimal("1") - fee)
                dfs(nxt, path + [nxt], leg_amt)

        dfs(src, [src], amount)

        if not best_path:
            return None

        # Build execution steps
        steps: List[ConversionStep] = []
        curr_amt = amount
        for i in range(len(best_path) - 1):
            u = best_path[i]
            v = best_path[i + 1]
            rate = self.matrix.get_conversion_rate(u, v)
            if rate is None:
                return None
            out_amt = curr_amt * rate * (Decimal("1") - fee)
            steps.append(
                ConversionStep(
                    from_currency=u,
                    to_currency=v,
                    rate=rate,
                    input_amount=curr_amt,
                    output_amount=out_amt,
                )
            )
            curr_amt = out_amt

        overall_effective_rate = curr_amt / amount

        # Compare with direct rate if available
        direct_rate = self.matrix.get_conversion_rate(src, dst)
        direct_out: Optional[Decimal] = None
        improvement_bps = Decimal("0")
        if direct_rate is not None:
            direct_out = amount * direct_rate * (Decimal("1") - fee)
            if direct_out > Decimal("0"):
                diff = curr_amt - direct_out
                improvement_bps = (diff / direct_out) * Decimal("10000")

        return RoutingPath(
            source_currency=src,
            target_currency=dst,
            steps=steps,
            overall_effective_rate=overall_effective_rate,
            initial_amount=amount,
            final_amount=curr_amt,
            direct_rate=direct_rate,
            improvement_bps=improvement_bps,
        )

    def convert(
        self,
        source: str,
        target: str,
        amount: Decimal,
        via: Optional[List[str]] = None,
        fee_rate: Optional[Decimal] = None,
    ) -> RoutingPath:
        """Execute conversion along explicit path or optimal path."""
        src = source.upper().strip()
        dst = target.upper().strip()
        fee = self.default_fee_rate if fee_rate is None else fee_rate

        if via:
            path = [src] + [c.upper().strip() for c in via] + [dst]
            steps: List[ConversionStep] = []
            curr_amt = amount
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i + 1]
                rate = self.matrix.get_conversion_rate(u, v)
                if rate is None:
                    raise ValueError(f"No direct quote or cross conversion available from {u} to {v}")
                out_amt = curr_amt * rate * (Decimal("1") - fee)
                steps.append(
                    ConversionStep(
                        from_currency=u,
                        to_currency=v,
                        rate=rate,
                        input_amount=curr_amt,
                        output_amount=out_amt,
                    )
                )
                curr_amt = out_amt
            overall_rate = curr_amt / amount
            direct_rate = self.matrix.get_conversion_rate(src, dst)
            improvement_bps = Decimal("0")
            if direct_rate:
                direct_out = amount * direct_rate * (Decimal("1") - fee)
                if direct_out > Decimal("0"):
                    improvement_bps = ((curr_amt - direct_out) / direct_out) * Decimal("10000")

            return RoutingPath(
                source_currency=src,
                target_currency=dst,
                steps=steps,
                overall_effective_rate=overall_rate,
                initial_amount=amount,
                final_amount=curr_amt,
                direct_rate=direct_rate,
                improvement_bps=improvement_bps,
            )

        best = self.find_best_route(src, dst, amount=amount, fee_rate=fee)
        if best is None:
            raise ValueError(f"No route found between {src} and {dst}")
        return best
