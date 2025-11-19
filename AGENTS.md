# AGENTS.md

## 🧭 Table of Contents
- [I. 🎯 Role of the Agent](#i--role-of-the-agent)
- [II. 📡 Data Source Architecture](#ii--data-source-architecture)
- [III. 🧱 Project Architecture](#iii--project-architecture)
- [IV. 📊 Common Signal Structure](#iv--common-signal-structure)
- [V. 🔀 Signal Types and Semantics](#v--signal-types-and-semantics)
  - [V.1 CEX → CEX](#v1-cex--cex)
  - [V.2 CEX → DEX / DEX → CEX](#v2-cex--dex--dex--cex)
  - [V.3 DEX → DEX](#v3-dex--dex)
  - [V.4 Futures Arbitrage (optional)](#v4-futures-arbitrage-optional)
- [VI. 📐 High / Medium / Low Classification](#vi--high--medium--low-classification)
- [VII. ⏱ Timestamp, Lifetime & Timeout](#vii--timestamp-lifetime--timeout)
- [VIII. 🔗 Contract Validation](#viii--contract-validation)
- [IX. ✉️ Message Builder Rules](#ix--message-builder-rules)
- [X. 🛠 Development Rules](#x--development-rules)
- [XI. 🔬 Data Source Testing Requirements](#xi--data-source-testing-requirements)

---

# I. 🎯 Role of the Agent

You are the persistent software engineer of the **ArbitrageWarner** project.

Your responsibilities:

- Build and maintain the full arbitrage scanning architecture.
- Use **Hummingbot Standalone Connectors** as the primary and preferred source of live CEX data.
- Use **DEX swap aggregators / pools** (Uniswap, 0x, fixed router APIs) for DEX-side data.
- Avoid all heavy dependencies:
  - ❌ Do NOT use HummingbotApplication  
  - ❌ Do NOT use MongoDB, Redis, motor  
  - ❌ Do NOT use quant-lab core/services/storage  
  - ❌ Do NOT use ccxt  
- Implement:
  - CEX → CEX arbitrage
  - CEX → DEX arbitrage
  - DEX → CEX arbitrage
  - DEX → DEX arbitrage (optional)
  - (Optional) Spot–Futures dislocations
- Compute all primary metrics:
  - `dif` — percentage difference  
  - `prof` — profit in USD  
  - `value` — used notional  
  - `amount` — in base currency  
  - `price` — VWAP price for given volume  
  - `chain` — networks for transfers (CEX–CEX)
- Implement:
  - timeouts  
  - lifetime tracking  
  - no-duplicate-signal system  
- Output Telegram-ready formatted messages.

### 🗣 Language Rules:
- All communication with the user — **in Russian**.  
- All code, comments, naming — **in English**.

---

# II. 📡 Data Source Architecture

## ✔ Primary data source: Hummingbot Standalone Connectors

Correct import style:

```python
from hummingbot.connector.exchange.binance.binance_exchange import BinanceExchange
Correct initialization:

python
Копировать код
connector = BinanceExchange(
    client_config_map=None,
    connector_name="binance",
    trading_pairs=["BTC-USDT"],
)

await connector.start_network()
await connector._order_book_tracker.start()
Data extraction:

python
Копировать код
ob = connector.order_book_tracker.order_books["BTC-USDT"]
bid = ob.get_price("bid")
ask = ob.get_price("ask")
bids = ob.bid_entries()
asks = ob.ask_entries()
Do NOT use:

❌ HummingbotApplication

❌ strategy runner

❌ UI / commands

❌ quant-lab storage / features

❌ Redis / MongoDB

❌ ccxt

✔ DEX-side data
Use direct API queries (HTTP) or quants-lab lightweight utilities for:

Uniswap pools

0x API

PancakeSwap / SushiSwap (via REST quote endpoints)

No heavy quant-lab framework.

III. 🧱 Project Architecture
graphql
Копировать код
project/
  core/
    data_sources/
      hb_cex.py             # standalone Hummingbot CEX data source
      hb_dex.py             # lightweight DEX quote provider
    models/
      orderbook.py          # depth / VWAP structures
      signal.py             # unified arbitrage signal model
    utils/
      formatting.py         # numerical/text formatting
      time.py               # timestamps, lifetime
      math.py               # helpers: dif, vwap, volumes
  screener/
    cex_cex.py              # CEX → CEX arbitrage logic
    cex_dex.py              # CEX → DEX arbitrage
    dex_cex.py              # DEX → CEX arbitrage
    classify.py             # dif classification
    timestamps.py           # deduplication / lifetime
    filters.py              # min dif, liquidity, blacklist
    message_builder.py      # Telegram formatting
    contract_validator.py   # optional
  config.yaml               # list of exchanges, pairs, thresholds
  main.py                   # entrypoint
Agent must create missing files/modules automatically.

IV. 📊 Common Signal Structure
All arbitrage signals share one structure:

python
Копировать код
class ArbitrageSignal:
    pair: str
    base: str
    quote: str

    signal_type: str        # "cex_cex", "cex_dex", "dex_cex", "dex_dex"
    direction: str

    sell_price: float
    amount: float
    value: float
    value_max: float

    rows: List[Dict]

    classification: str     # "high" | "medium" | "low"

    timestamp: float
    lifetime_sec: float
rows example:

json
Копировать код
{
  "exc": "binance",
  "dif": 8.2,
  "prof": 240,
  "value": 3000,
  "price": 0.002201,
  "chain": "ERC20"
}
V. 🔀 Signal Types and Semantics
V.1 CEX → CEX
Most important module.

Flow:

Get VWAP buy prices from all exchanges.

Get VWAP sell prices from all exchanges.

Find:

best buy exchange

best sell exchange

dif = (sell - buy) / buy * 100

Produce arbitrage signal if above threshold.

V.2 CEX → DEX / DEX → CEX
DEX data via:

Uniswap V2/V3 quote

0x swap quote

direct pool price

Flow:

Compute CEX VWAP buy/sell.

Compute DEX swap quote for volume.

Build signal:

direction: "CEX → Ethereum" or "DEX → CEX"

Contract validator (optional):

matching contract → show “verified”

mismatch → block CEX–DEX signals

V.3 DEX → DEX
Not blocked by contract mismatch.
Provide contracts for clarity.

V.4 Futures Arbitrage (optional)
If added:

use futures connectors (Binance/Bybit futures)

include funding rates if available.

VI. 📐 High / Medium / Low Classification
Values can be configured in config.yaml, but default:

High — dif ≥ 30%

Medium — 10% ≤ dif < 30%

Low — 1% ≤ dif < 10%

Used for filtering and message tagging.

VII. ⏱ Timestamp, Lifetime & Timeout
File: timestamps.py

store first_seen and last_sent

identity:

python
Копировать код
f"{signal_type}:{pair}:{buy_exc}:{sell_exc}"
Rules:

First detection → send immediately

Subsequent detections:

update lifetime

if too soon (< timeout_sec) → do not send

VIII. 🔗 Contract Validation
For CEX–DEX and DEX–CEX:
If both contract addresses are known and match → OK

If both known and mismatch → ❌ block signal

If only one known → allow but do NOT show contract line

For DEX–DEX:
Do NOT block for mismatch

Show contracts for transparency

IX. ✉️ Message Builder Rules
Message format:

yaml
Копировать код
BTC (8.2%)
CEX ➜ CEX

sell price: 0.002201$
amount: 153000
value: 3000$ (max 3200$)

exc | dif | prof | value | price | chain
----------------------------------------
Binance | 8.2% | 240$ | 3000 | 0.00221 | ERC20
OKX     | 8.1% | 235$ | 3000 | 0.00222 | ERC20

Lifetime: 3 minutes
Rules:

align columns cleanly

use formatted numbers

show lifetime

show direction

show contract match if applicable

include DEX pool link when relevant

X. 🛠 Development Rules
Agent MUST:

Always follow this file as authoritative specification.

Keep code modular and readable.

Use async everywhere data is fetched.

Add docstrings and type hints.

Avoid duplication; refactor when needed.

Never ask unnecessary clarification if the intention is obvious.

Never break the architectural boundaries.

Agent MUST NOT:

import or start HummingbotApplication

incorporate quant-lab storage/core/services

add MongoDB, Redis, motor

use ccxt

bypass DataSource modules

XI. 🔬 Data Source Testing Requirements
Before using any DataSource module in arbitrage logic:

✔ CEX DataSource tests:
connector starts

orderbook tracker receives data

best bid/ask works

VWAP for given amount works

exceptions are handled

✔ DEX DataSource tests:
quotes load

slippage calculation correct

pool contract read OK

✔ Arbitrage direction tests:
CEX–CEX price difference deterministic

CEX–DEX volume fit

contract verification logic works

✔ Lifetime tests:
repeat signals suppressed

lifetime increases

first_seen stays stable

last_sent updated correctly

✔ Message builder tests:
output formatted exactly

numerical formatting correct

table sorted

End of file