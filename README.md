# fx-arbitrage-router

Foreign Exchange (FX) Cross-Currency Arbitrage Scanner and Multi-Leg Routing Engine.

`fx-arbitrage-router` models institutional FX spot order books, detects multi-currency triangular and cycle arbitrage using log-transformed Bellman-Ford graph algorithms, and identifies optimal conversion routes across illiquid or wide-spread currency pairs.

Built exclusively with zero external dependencies using the Python standard library.

## Key Capabilities

1. Multi-Currency Spot Matrix: Parses direct quotes, handles bid/ask spreads, and computes synthetic cross-rates with basis-point spread analytics.
2. Triangular and Multi-Leg Arbitrage: Detects riskless execution loops across currency networks accounting for transaction fees, slippage, and spread decay.
3. Bellman-Ford Negative Cycle Detection: Evaluates \(-\ln(R_{u \to v} \cdot (1 - f))\) edge weights to identify arbitrary negative-weight cycles representing arbitrage profits.
4. Optimal Execution Routing: Calculates high-efficiency multi-hop routes (e.g. AUD -> USD -> JPY) when cross-currency liquidity or spreads outperform direct conversion pairs.
5. Exact Financial Precision: Uses Python standard `decimal.Decimal` throughout all pricing calculations to eliminate floating point rounding errors.

## Installation

```bash
pip install .
```

## CLI Usage

### 1. View FX Spot Rate Matrix

```bash
fxrouter matrix
```

### 2. Scan for Triangular Arbitrage Opportunities

```bash
fxrouter arbitrage --fees-bps 3.0 --method triangular
```

### 3. Detect Negative Cycles with Bellman-Ford

```bash
fxrouter arbitrage --fees-bps 2.0 --method bellman
```

### 4. Find Optimal Multi-Leg Conversion Route

```bash
fxrouter route AUD JPY --amount 50000 --fees-bps 5.0
```

### 5. Simulate Step-by-Step Multi-Leg Conversion

```bash
fxrouter convert EUR JPY 10000 --via USD --fees-bps 5.0
```

### 6. Inject Custom Spot Quotes

```bash
fxrouter --quote EUR/USD=1.0900:1.0902 --quote USD/JPY=155.00:155.05 matrix
```

## Python API Usage

```python
from decimal import Decimal
from fx_arbitrage_router import RateMatrix, ArbitrageEngine, FXRouter

# 1. Initialize matrix
matrix = RateMatrix.load_sample_market()

# 2. Scan for triangular arbitrage
engine = ArbitrageEngine(matrix, fee_rate=Decimal("0.0005"))
opps = engine.scan_triangular()
for opp in opps:
    print(opp.summary())

# 3. Compute best conversion route
router = FXRouter(matrix, default_fee_rate=Decimal("0.0005"))
route = router.find_best_route(source="AUD", target="JPY", amount=Decimal("25000"))
if route:
    print(route.summary())
```

## License

MIT License. Open source for institutional banking and algorithmic treasury operations.
