"""Data models for FX quotes, conversion routes, and arbitrage opportunities."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Dict, Optional, Any


@dataclass
class CurrencyQuote:
    base_currency: str
    quote_currency: str
    bid: Decimal
    ask: Decimal
    timestamp: str = ""

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal("2")

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid

    @property
    def spread_bps(self) -> Decimal:
        if self.mid == Decimal("0"):
            return Decimal("0")
        return (self.spread / self.mid) * Decimal("10000")


@dataclass
class ConversionStep:
    from_currency: str
    to_currency: str
    rate: Decimal
    input_amount: Decimal
    output_amount: Decimal


@dataclass
class RoutingPath:
    source_currency: str
    target_currency: str
    steps: List[ConversionStep] = field(default_factory=list)
    overall_effective_rate: Decimal = Decimal("1")
    initial_amount: Decimal = Decimal("1")
    final_amount: Decimal = Decimal("1")
    direct_rate: Optional[Decimal] = None
    improvement_bps: Decimal = Decimal("0")

    def summary(self) -> str:
        path_str = " -> ".join([self.source_currency] + [s.to_currency for s in self.steps])
        lines = [
            f"Optimal Route:     {path_str}",
            f"Input Amount:      {self.initial_amount:.4f} {self.source_currency}",
            f"Final Output:      {self.final_amount:.4f} {self.target_currency}",
            f"Effective Rate:    {self.overall_effective_rate:.6f}",
        ]
        if self.direct_rate:
            lines.append(f"Direct Rate:       {self.direct_rate:.6f}")
            lines.append(f"Route Advantage:   +{self.improvement_bps:.2f} bps")
        lines.append("Execution Steps:")
        for idx, s in enumerate(self.steps, start=1):
            lines.append(
                f"  [{idx}] Convert {s.input_amount:.4f} {s.from_currency} -> {s.output_amount:.4f} {s.to_currency} (Rate: {s.rate:.6f})"
            )
        return "\n".join(lines)


@dataclass
class ArbitrageOpportunity:
    cycle: List[str]
    gross_multiplier: Decimal
    net_multiplier: Decimal
    profit_pct: Decimal
    net_return_bps: Decimal
    execution_steps: List[str] = field(default_factory=list)

    def summary(self) -> str:
        cycle_str = " -> ".join(self.cycle)
        lines = [
            f"Arbitrage Cycle:   {cycle_str}",
            f"Gross Multiplier:  {self.gross_multiplier:.6f}x",
            f"Net Multiplier:    {self.net_multiplier:.6f}x (after fees)",
            f"Profit Margin:     +{self.profit_pct:.4f}% (+{self.net_return_bps:.2f} bps)",
            "Execution Sequence:",
        ]
        for step in self.execution_steps:
            lines.append(f"  - {step}")
        return "\n".join(lines)
