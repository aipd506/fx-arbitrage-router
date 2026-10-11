"""Arbitrage cycle detection engine using Bellman-Ford and cycle enumerators."""

import math
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple
from .models import ArbitrageOpportunity
from .rates import RateMatrix


class ArbitrageEngine:
    """Detects triangular and multi-leg FX arbitrage opportunities."""

    def __init__(self, matrix: RateMatrix, fee_rate: Decimal = Decimal("0.0005")):
        """
        fee_rate: Transaction fee / slippage penalty per leg (e.g. 0.0005 = 5 bps).
        """
        self.matrix = matrix
        self.fee_rate = fee_rate

    def scan_triangular(self) -> List[ArbitrageOpportunity]:
        """Exhaustively scan all 3-currency cycles for positive arbitrage."""
        currencies = self.matrix.get_all_currencies()
        opportunities: List[ArbitrageOpportunity] = []
        seen_cycles: Set[Tuple[str, ...]] = set()

        for a in currencies:
            for b in currencies:
                if a == b:
                    continue
                r_ab = self.matrix.get_conversion_rate(a, b)
                if r_ab is None:
                    continue
                for c in currencies:
                    if c == a or c == b:
                        continue
                    r_bc = self.matrix.get_conversion_rate(b, c)
                    r_ca = self.matrix.get_conversion_rate(c, a)
                    if r_bc is None or r_ca is None:
                        continue

                    # Gross multiplier: r_ab * r_bc * r_ca
                    gross = r_ab * r_bc * r_ca
                    # Net multiplier accounting for fees per leg: r * (1 - fee)
                    fee_factor = Decimal("1") - self.fee_rate
                    net = (r_ab * fee_factor) * (r_bc * fee_factor) * (r_ca * fee_factor)

                    if net > Decimal("1"):
                        # Canonical cycle representation to avoid reporting shifted duplicates (A-B-C-A == B-C-A-B)
                        cycle = [a, b, c, a]
                        canon = self._canonical_cycle([a, b, c])
                        if canon in seen_cycles:
                            continue
                        seen_cycles.add(canon)

                        profit_pct = (net - Decimal("1")) * Decimal("100")
                        net_bps = (net - Decimal("1")) * Decimal("10000")
                        steps = [
                            f"Sell {a} for {b} at effective rate {r_ab:.6f}",
                            f"Sell {b} for {c} at effective rate {r_bc:.6f}",
                            f"Sell {c} for {a} at effective rate {r_ca:.6f}",
                        ]
                        opportunities.append(
                            ArbitrageOpportunity(
                                cycle=cycle,
                                gross_multiplier=gross,
                                net_multiplier=net,
                                profit_pct=profit_pct,
                                net_return_bps=net_bps,
                                execution_steps=steps,
                            )
                        )

        # Sort descending by profit_pct
        opportunities.sort(key=lambda opp: opp.profit_pct, reverse=True)
        return opportunities

    def scan_all_cycles(self, max_depth: int = 4) -> List[ArbitrageOpportunity]:
        """Scan cycles up to max_depth legs (2 to max_depth) using depth-first search."""
        currencies = self.matrix.get_all_currencies()
        opportunities: List[ArbitrageOpportunity] = []
        seen_cycles: Set[Tuple[str, ...]] = set()

        def dfs(current: str, start: str, path: List[str], current_gross: Decimal, current_net: Decimal, steps: List[str]):
            if len(path) > max_depth + 1:
                return

            if len(path) >= 3 and current == start:
                # Completed cycle
                if current_net > Decimal("1"):
                    canon = self._canonical_cycle(path[:-1])
                    if canon not in seen_cycles:
                        seen_cycles.add(canon)
                        profit_pct = (current_net - Decimal("1")) * Decimal("100")
                        net_bps = (current_net - Decimal("1")) * Decimal("10000")
                        opportunities.append(
                            ArbitrageOpportunity(
                                cycle=list(path),
                                gross_multiplier=current_gross,
                                net_multiplier=current_net,
                                profit_pct=profit_pct,
                                net_return_bps=net_bps,
                                execution_steps=list(steps),
                            )
                        )
                return

            for nxt in currencies:
                # If closing cycle, must be start; else cannot re-visit path nodes
                if nxt == start:
                    if len(path) < 3:
                        continue
                elif nxt in path:
                    continue

                rate = self.matrix.get_conversion_rate(current, nxt)
                if rate is None:
                    continue

                fee_factor = Decimal("1") - self.fee_rate
                net_leg = rate * fee_factor
                step_desc = f"Convert {current} to {nxt} at {rate:.6f}"

                dfs(
                    current=nxt,
                    start=start,
                    path=path + [nxt],
                    current_gross=current_gross * rate,
                    current_net=current_net * net_leg,
                    steps=steps + [step_desc],
                )

        for ccy in currencies:
            dfs(current=ccy, start=ccy, path=[ccy], current_gross=Decimal("1"), current_net=Decimal("1"), steps=[])

        opportunities.sort(key=lambda opp: opp.profit_pct, reverse=True)
        return opportunities

    def detect_negative_cycle_bellman_ford(self) -> Optional[ArbitrageOpportunity]:
        """
        Bellman-Ford algorithm over log-transformed rates to find negative cycles.
        Weight w(u, v) = -ln(rate * (1 - fee_rate)).
        A negative weight cycle corresponds to product(rate * (1 - fee_rate)) > 1.
        """
        currencies = self.matrix.get_all_currencies()
        if not currencies:
            return None

        # Build edge list
        edges: List[Tuple[str, str, float, Decimal]] = []
        fee_factor = float(Decimal("1") - self.fee_rate)

        for u in currencies:
            for v in currencies:
                if u == v:
                    continue
                rate = self.matrix.get_conversion_rate(u, v)
                if rate is not None and rate > Decimal("0"):
                    effective = float(rate) * fee_factor
                    if effective > 0:
                        weight = -math.log(effective)
                        edges.append((u, v, weight, rate))

        # Run Bellman-Ford initialized with dist 0 everywhere
        dist: Dict[str, float] = {c: 0.0 for c in currencies}
        pred: Dict[str, Optional[str]] = {c: None for c in currencies}
        edge_rate: Dict[Tuple[str, str], Decimal] = {}
        for u, v, w, r in edges:
            edge_rate[(u, v)] = r

        # Relax |V| - 1 times
        for _ in range(len(currencies) - 1):
            relaxed = False
            for u, v, w, _ in edges:
                if dist[u] + w < dist[v] - 1e-12:
                    dist[v] = dist[u] + w
                    pred[v] = u
                    relaxed = True
            if not relaxed:
                break

        # Check for negative weight cycle
        cycle_start: Optional[str] = None
        for u, v, w, _ in edges:
            if dist[u] + w < dist[v] - 1e-12:
                cycle_start = v
                break

        if not cycle_start:
            return None

        # Trace back to find cycle
        curr = cycle_start
        for _ in range(len(currencies)):
            if pred[curr] is not None:
                curr = pred[curr]

        cycle: List[str] = [curr]
        p = pred[curr]
        while p is not None and p != curr:
            cycle.append(p)
            p = pred[p]
        cycle.append(curr)
        cycle.reverse()

        # Calculate exact Decimal figures
        gross = Decimal("1")
        net = Decimal("1")
        fee_dec = Decimal("1") - self.fee_rate
        steps: List[str] = []

        for i in range(len(cycle) - 1):
            from_c = cycle[i]
            to_c = cycle[i + 1]
            r = self.matrix.get_conversion_rate(from_c, to_c)
            if r is None:
                return None
            gross *= r
            net *= (r * fee_dec)
            steps.append(f"Convert {from_c} to {to_c} at {r:.6f}")

        if net <= Decimal("1"):
            return None

        profit_pct = (net - Decimal("1")) * Decimal("100")
        net_bps = (net - Decimal("1")) * Decimal("10000")

        return ArbitrageOpportunity(
            cycle=cycle,
            gross_multiplier=gross,
            net_multiplier=net,
            profit_pct=profit_pct,
            net_return_bps=net_bps,
            execution_steps=steps,
        )

    def _canonical_cycle(self, nodes: List[str]) -> Tuple[str, ...]:
        """Rotate cycle so that lowest lexicographical currency is first."""
        if not nodes:
            return tuple()
        min_idx = nodes.index(min(nodes))
        rotated = nodes[min_idx:] + nodes[:min_idx]
        return tuple(rotated)
