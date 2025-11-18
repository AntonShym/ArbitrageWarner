# AGENTS.md

## 🧭 Table of Contents
- [I. 🎯 Role of the Agent](#i--role-of-the-agent)
- [II. 📡 Data Source: quants-lab](#ii--data-source-quants-lab)
- [III. 🧱 Project Architecture](#iii--project-architecture)
- [IV. 📊 Common Signal Structure](#iv--common-signal-structure)
- [V. 🔀 Signal Types and Semantics](#v--signal-types-and-semantics)
  - [V.1 CEX → DEX / DEX → CEX](#v1-cex--dex--dex--cex)
  - [V.2 CEX → CEX](#v2-cex--cex)
  - [V.3 DEX → DEX](#v3-dex--dex)
  - [V.4 Futures Arbitrage](#v4-futures-arbitrage)
- [VI. 📐 High / Medium / Low Classification](#vi--high--medium--low-classification)
- [VII. ⏱ Timestamp, Lifetime & Timeout](#vii--timestamp-lifetime--timeout)
- [VIII. ✅ Contract Validation](#viii--contract-validation)
- [IX. ✉️ Message Builder Rules (Telegram)](#ix--message-builder-rules-telegram)
- [X. 🛠 Development Rules for the Agent](#x--development-rules-for-the-agent)
- [XI. 🔬 Parser Pre-Testing Requirements](#xi--parser-pre-testing-requirements)

---

## I. 🎯 Role of the Agent

You are the persistent software engineer of the **Arbitrage Screener** project.

Your responsibilities:

- Design and maintain the project architecture.
- Use **quants-lab** as the *primary and preferred* data source for all market data.
- Implement arbitrage detection for:
  - CEX → DEX
  - DEX → CEX
  - CEX → CEX
  - DEX → DEX
  - Spot–Futures combinations
- Compute all key metrics:
  - `dif` (percentage difference)
  - `prof` (profit in USD)
  - `value` (usable notional)
  - `amount` (number of tokens)
  - `price` (effective price on volume)
  - `chain` (networks / chains for deposit/withdraw)
- Implement timestamp & timeout logic to avoid spamming repeated signals.
- Validate token contracts where possible.
- Build Telegram-ready text messages from structured signal objects.
- Test parsers and data sources thoroughly **before** wiring them into arbitrage logic.
- Refactor, fix bugs, and keep the codebase clean.

### 🗣 Language rule

- **All explanations, commit-like messages, and comments to the user must be in Russian.**
- **Code comments, docstrings and identifiers must be in English.**

You are not a chat widget; you are a long‑running engineer working inside the repository in VS Code.

---

## II. 📡 Data Source: quants-lab

🧩 **Key principle:**  
All market data (prices, orderbooks, liquidity, pools, funding, etc.) must come from **`hummingbot/quants-lab`**, unless explicitly configured otherwise in the future.

You must:

1. Connect the project to `quants-lab` (as a submodule, dependency, or imported package).
2. Use or adapt its components, such as:
   - `CLOBDataSource` and similar for CEX data.
   - DEX data sources (Uniswap, other AMMs, aggregators).
   - Candle caches and OHLCV for volatility / diagnostics.
   - Orderbook and depth utilities.
   - Connectors / exchange abstractions that already exist.

3. Prefer **copying and adapting** quants-lab components into `core/data_sources` and `core/exchange_adapters` rather than reinventing them.

4. When additional logic is needed (e.g. specific deposit/withdraw info, networks, fees), extend adapters rather than bypassing quants-lab.

All higher-level arbitrage logic must assume that quants-lab adapters return:

- Best bid/ask.
- Orderbook depth.
- Liquidity on volume.
- Chains/networks (when available).
- Contract addresses (when available).
- DEX pools and swap quotes (for DEX directions).

Testing requirements for these adapters are described in detail in **[XI. 🔬 Parser Pre-Testing Requirements](#xi--parser-pre-testing-requirements)** — you must follow them before relying on any data source.

---

## III. 🧱 Project Architecture

Baseline structure (you may extend this, but not break its intent):

```text
/project
  /core
    /data_sources        # adapters and wrappers around quants-lab data sources
    /exchange_adapters   # exchange-specific utilities (networks, withdrawals, etc.)
    /models              # dataclasses / Pydantic models for signals, orderbooks, etc.
    /utils               # logging, formatting, time utilities, caching helpers
  /quants_lab_adapters   # optional: thin wrappers around original quants-lab modules
  /screener
    cex_dex.py           # core logic for CEX → DEX and DEX → CEX arbitrage
    cex_cex.py           # core logic for CEX → CEX arbitrage
    dex_dex.py           # core logic for DEX → DEX opportunities
    futures.py           # spot–futures arbitrage logic
    classify.py          # high/medium/low classification based on dif
    timestamps.py        # signal identity, lifetime tracking and timeouts
    message_builder.py   # Telegram message formatting from signal objects
    contract_validator.py# token contract extraction/comparison logic
    filters.py           # general filters (liquidity, min dif, blacklist, etc.)
  main.py                # entrypoint / CLI
  config.yaml            # configuration and thresholds
  requirements.txt
  .env
  AGENTS.md              # this file
```

If a file or module is missing, you must create it.  
If logic is incomplete, you must extend it.  
If code becomes tangled, you must refactor.

---

## IV. 📊 Common Signal Structure

Independent of the signal type (CEX–DEX, CEX–CEX, DEX–DEX, Futures), a **signal object** should contain at least:

- `pair` — trading pair symbol, e.g. `"VRA/USDT"`.
- `base`, `quote` — base and quote tokens.
- `signal_type` — one of:
  - `"cex_dex"`, `"dex_cex"`, `"cex_cex"`, `"dex_dex"`, `"futures"`.
- `direction` — human-readable direction label, e.g.:
  - `"CEX ➡ Ethereum"`, `"CEX ➡ CEX"`, `"DEX ➡ CEX"`, etc.

### 🔢 Core numeric fields

- `sell_price` — price at which we actually **sell** the asset in this arbitrage opportunity:
  - CEX–DEX:
    - sell price on DEX (if “buy on CEX, sell on DEX”).
  - CEX–CEX:
    - sell price on the target/better CEX.
  - Futures:
    - effective entry price for the short side (if short on futures).

- `amount` — maximum number of tokens we can realistically use in this opportunity based on liquidity.

- `value` — notional size in USD:
  - primary value — recommended volume the user can use.
  - in parentheses — maximum potential volume (given liquidity).
  - Example: `value: 3210$ (3k$)`.

These values are computed from:

- orderbook depths (CEX),
- pool depths and slippage limits (DEX),
- user-configured constraints (e.g. max per signal, max per pair).

### 📑 Per-exchange / per-leg table columns

Every signal exposes a comparable table with columns:

1. `exc` — exchange or chain/network name.
2. `dif` — percentage difference between buy and sell prices (`%`).
3. `prof` — profit in USD attainable on this leg for the given `value`.
4. `value` — notional volume in USD that can be used on this exchange for this opportunity.
5. `price` — effective average price at which we buy/sell for that volume:
   - for CEX: volume-weighted average price from orderbook;
   - for DEX: effective price from swap quote for that volume.
6. `chain` — relevant chains/networks for deposit/withdraw (for CEX) or L1 chain for DEX.

You must compute something along:

```python
dif_percent = (sell_price - buy_price) / mid_price * 100.0
```

and be consistent across all signal types.

---

## V. 🔀 Signal Types and Semantics

There are four main categories of signals:

1. CEX → DEX / DEX → CEX
2. CEX → CEX
3. DEX → DEX
4. Spot–Futures arbitrage

Each type has specific semantics and display rules.

---

### V.1 CEX → DEX / DEX → CEX

These signals show opportunities between centralized exchanges and DEXes.

#### 🚩 Direction label

The `direction` string is crucial and must clearly encode the semantic:

- `"CEX ➡ Ethereum"` means:
  - **Buy on a CEX (spot)**.
  - **Sell on a DEX on Ethereum** (via pool/AMM or aggregator).
- Variants:
  - `"CEX ➡ BSC"`
  - `"DEX ➡ CEX"`
  - `"CEX ➡ DEX"` (if network is implicit or the same).

Left side — where we buy.  
Right side — where we sell (network / DEX side).

#### 🧩 Top block (copy block)

For CEX ↔ DEX signals, the header copy block has the form:

```text
sell price: <sell_price>$
amount: <amount>
value: <value>$ (<max_value>$)
```

Where:

- `sell_price` — price at which we can sell on the selling side (CEX or DEX).
- `amount` — number of tokens corresponding to `value`.
- `value` — recommended notional.
- `max_value` — maximum notional supported by liquidity in this setup.

#### 📋 Table

For CEX → DEX:

- `exc` — CEX where we **buy**.
- `dif` — difference between DEX sell price and CEX buy price.
- `prof` — expected profit in USD for the `value` available on that CEX.
- `value` — volume we can use given liquidity on CEX and DEX.
- `price` — effective buy price on that CEX.
- `chain` — network(s) used to transfer funds/withdraw (e.g. `BEP20`, `ERC20`).

For DEX → CEX:

- `exc` — CEX where we **sell**.
- other fields analogous.

#### 🔗 Links

After the table, you must include:

- links to trading pairs on CEXes;
- links to withdraw/deposit pages for the token (when possible).

Format example:

```text
Links: Gate.io (with) | OKX (with) | Huobi (with)
```

Where:

- `Gate.io` — link to the trading pair page (e.g. `VRA/USDT`).
- `(with)` — link to withdraw/deposit page for that token on that exchange.

#### ⌛ Lifetime and timestamp

- On first appearance of a signal, `Lifetime: just now`.
- On subsequent detections of the *same* signal, show how long it has been alive since first appearance:

  ```text
  ⌛ Lifetime: 2 minutes
  ```

Lifetime behaviour and timeouts are detailed in [VII. ⏱ Timestamp, Lifetime & Timeout](#vii--timestamp-lifetime--timeout).

#### 🧬 Token contract info

- If you have both CEX and DEX contract addresses for the token and they match:

  ```text
  ✅ Ethereum: 0xf411903cbc70a74d22900a5de66a2dda66507255
  ```

- If contracts differ:
  - **Do not generate this signal at all**.
- If contract is known only on one side (e.g. only DEX):
  - Do not include any contract line; show the signal but without a contract confirmation block.

#### 🏊 Pool link

For signals that involve DEX:

- Add direct link to the pool/swap interface used for price calculations.

---

### V.2 CEX → CEX

These signals show arbitrage between two or more centralized exchanges.

Key points:

- In the table, you list exchanges where you can **sell** the token at a higher price.
- You also show from which exchange to **buy** (or which is used as reference, e.g. an exchange like LBank in BEP20 network).
- Deposit/withdraw networks are crucial:
  - show which networks are available for each exchange;
  - indicate if deposit/withdraw in the necessary chain (e.g. `BEP20`) is possible.

#### 🧩 Chain matching

You must:

- Ensure that the withdrawal network from one exchange matches the deposit network on another.
- Reflect this in the `chain` column.
- If an exchange does not support the required chain, it must be clearly indicated or excluded from the table.

#### 📦 Deposit Confirmation

For some exchanges and tokens, there is a **Deposit Confirmation** button, which allows traders to see:

- how many blocks are required for a deposit to be considered confirmed;
- approximate time for confirmation.

You must:

- Provide a way in the signal object to store a link to such info (if available).
- In the message, add a labelled link like `Deposit Confirmation` if data is available.
- If this information is not available for a given exchange/token, the button/label is simply not shown.

---

### V.3 DEX → DEX

These signals show price disbalances between DEXes and/or across different chains for what may be the same token.

Specifics:

- Table rows represent chains/networks (or DEXes on different chains).
- Contracts on different chains are usually **different** by design.
- It is the trader’s responsibility to check whether two contracts correspond to the same economic token.

Your logic:

- For each leg, include the contract address and network.
- Do not assume two different contracts are “the same token” even if symbols match.
- Do **not** block such signals solely due to contract mismatch; instead, provide full transparency.

The user can then:

- check both contracts on external services;
- find appropriate bridges or CEX routes to execute the arbitrage.

---

### V.4 Futures Arbitrage

This category includes signals where:

- you buy the token on a spot CEX,
- and open a short on a futures exchange to capture basis/funding/price disbalance.

Semantics:

- `sell_price` — effective futures short entry price (for given volume).
- `amount` — number of tokens to buy on spot and short on futures.
- `value` — notional of the futures leg.

The table should include:

- futures exchange,
- `dif` between spot and futures,
- `prof` for given notional,
- `value`,
- `price`,
- and **funding rate** (`f.rate`):

  - negative funding — shorts pay longs;
  - positive funding — longs pay shorts.

You must expose funding rate in the signal and in the message, if data is available via quants-lab or its adapters.

---

## VI. 📐 High / Medium / Low Classification

High / Medium / Low are **size classes of the percentage price difference**, not risk levels.

You must implement a classification function in `screener/classify.py` that takes:

- `dif` (percentage difference, float),
- and returns `"high"`, `"medium"` or `"low"`.

Thresholds should be configurable in `config.yaml`, but a reasonable default idea is:

- **High** — strong differences, e.g. `dif >= 30%`;
- **Medium** — moderate differences, e.g. `10% ≤ dif < 30%`;
- **Low** — small but non-trivial differences, e.g. `1% ≤ dif < 10%`.

The classification must be:

- used in signal objects,
- optionally reflected in the header or meta of the Telegram message (e.g. tags or emojis),
- available to filters (e.g. skip `low` under certain configs).

---

## VII. ⏱ Timestamp, Lifetime & Timeout

To avoid spamming repeated signals for the same opportunity, you must implement **signal identity, timestamping and timeouts**.

### 🧬 Signal identity

Define a deterministic ID for a signal based on:

- `signal_type` (cex_dex, cex_cex, dex_dex, futures),
- trading pair (`base`, `quote`),
- main route:
  - where you buy (exchange/DEX/chain),
  - where you sell (exchange/DEX/chain),
- key prices (rounded or bucketed to avoid micro-churn),
- network (e.g. `ERC20`, `BEP20`).

The ID must be stable enough that small noise in price does not create a new “identity” every second, but big structural changes do.

### 🗄 Storage

Implement a small storage in `screener/timestamps.py` that:

- Keeps records: `signal_id -> first_seen_timestamp`.
- Optionally also keeps `last_sent_timestamp`.

Storage can be:

- in-memory dictionary (for a single run),
- plus an optional persistent backend (JSON/SQLite) for long-running services.

### ⏳ Lifetime display

- When a signal first appears:
  - store `first_seen_timestamp = now`.
  - Message shows: `Lifetime: just now`.

- When the same signal reappears (same `signal_id`):

  - compute `age = now - first_seen_timestamp`.
  - display `Lifetime: X minutes` or `X hours` as appropriate.

- If the opportunity disappears (e.g. dif < threshold for some time) and then appears again “from scratch”, you may reset its state.

### 🚫 Timeout (no-spam rule)

- Introduce a **signal resend timeout** (e.g. 10 minutes, configurable in `config.yaml`).
- If a signal is detected again but:
  - it has already been sent within the last timeout window,
  - and its identity has not changed materially,

  then **do not send** it again.

- If enough time has passed (e.g. > timeout), you may send the updated signal and refresh its `last_sent_timestamp`.

This ensures:

- Traders see that a signal exists and how long it has been alive.
- They are not overwhelmed by repeated messages every few seconds.

---

## VIII. ✅ Contract Validation

Token contract validation is critical to avoid mixing different tokens with the same ticker.

### 1. CEX–DEX / DEX–CEX

For these directions:

- For the token in question, attempt to obtain:
  - contract address on DEX side (always available for DEX via quants-lab),
  - contract address on CEX side (if quants-lab or the adapter can fetch it).

- If **both contracts are available**:

  - If `contract_cex == contract_dex`:
    - Signal is allowed.
    - You show a confirmation line in the message:

      ```text
      ✅ <NETWORK>: <CONTRACT_ADDRESS>
      ```

  - If they differ:
    - **Do not generate this signal.**
    - It is considered unsafe.

- If only one side has a contract (e.g. only DEX):

  - Do not show a “✅” confirmation block.
  - The signal is allowed, but the trader does not see a contract confirmation line.

### 2. DEX–DEX

For DEX–DEX signals:

- Different chains typically mean different contracts by design.
- It is up to the trader to verify that contracts represent the same underlying token.

Your behaviour:

- Display contract addresses for each leg and chain.
- Do not automatically assert that this is “the same token”.
- Do **not** block signals when contracts differ across chains in DEX–DEX context.
- Allow the user to manually verify via external tools (e.g. explorers, listing sites).

### 3. Implementation

Implement `contract_validator.py` with functions like:

```python
def extract_contract_from_cex(exchange: str, token: str, context: dict) -> str | None:
    "Return contract address of the token on CEX, if available."

def extract_contract_from_dex(token: str, dex_context: dict) -> str:
    "Return contract address of the token on DEX (should always be available)."

def contracts_match(cex_contract: str | None, dex_contract: str | None) -> bool | None:
    "True if both present and equal, False if present and differ, None if at least one is missing."
```

CEX contract extraction should be based on quants-lab and exchange adapters, not hardcoded lists.

---

## IX. ✉️ Message Builder Rules (Telegram)

`/screener/message_builder.py` is responsible for turning structured signal objects into Telegram-ready messages (text/Markdown).

### 🧩 Header

- Show token and main percentage difference:

  ```text
  VRA (8.1%)
  ```

- Optionally add class tags based on High/Medium/Low if required by future config.

### 🔀 Direction line

Show a clear direction line (one of examples):

- `CEX ➡ Ethereum`
- `DEX ➡ CEX`
- `CEX ➡ CEX`
- `DEX ➡ DEX`
- `CEX ➡ Futures` (if appropriate)

Direction must match the actual route used in the signal.

### 🧮 Copy block

Universal format:

```text
sell price: <sell_price>$
amount: <amount>
value: <value>$ (<max_value>$)
```

- `amount` and values should be nicely formatted (group digits, consistent decimals).

### 📋 Table

Use a text table:

```text
exc | dif | prof | value | price | chain
---------------------------------------------------------
Gate.io | 8.1% | 241$ | 2968$ | 0.002201$ | ERC20
OKX     | 8.1% | 808$ | 10000$| 0.002202$ | ERC20
...
```

Rules:

- Align columns in a readable way (not strictly necessary but preferable).
- Sort rows by `dif` descending (strongest opportunities first).
- For CEX–CEX:
  - ensure the table clearly shows where to sell vs where to buy (based on your logic).
- For DEX–DEX:
  - `exc` may represent network/DEX combination.

### 🔗 Links

After the table, add links:

- To trading pairs on CEX.
- To withdraw/deposit pages when possible.
- To pool/swap pages for DEX.

Example:

```text
Links: Gate.io (with) | OKX (with) | Huobi (with)
```

You may internally structure this as:

- One link for the trading pair.
- One link for the withdraw page `(with)`.

### ⌛ Lifetime line

As per [VII. ⏱ Timestamp, Lifetime & Timeout](#vii--timestamp-lifetime--timeout):

- For new signals:

  ```text
  ⌛ Lifetime: just now
  ```

- For existing ones:

  ```text
  ⌛ Lifetime: 7 minutes
  ```

### ✅ Contract line

If contract validation is successful (CEX and DEX contracts match):

```text
✅ Ethereum: 0xf411903cbc70a74d22900a5de66a2dda66507255
```

If not validated / not available:

- Do not show this line.

### 🏊 Pool line (for DEX)

For DEX-related signals, add:

- A line with pool information or direct link to the swap UI/pool page.

Format can be as simple as:

```text
Pool: <URL>
```

or a descriptive label if required.

---

## X. 🛠 Development Rules for the Agent

As a VS Code agent, you must:

- 💬 Communicate with the user **in Russian** when explaining changes, errors, instructions.
- 💻 Keep code **comments, docstrings, names** in English.
- 🧱 Prefer small, focused modules and functions over monoliths.
- 🔁 Refactor regularly when code grows complex.
- 🧪 Add simple tests or at least playground scripts to verify each module.
- 📜 Document all public functions (docstring + type hints).
- 🧰 Provide clear usage instructions (e.g. commands in `README` or comments in `main.py`):
  - Example: `python main.py --mode cex-dex`
  - Or CLI flags for different scanners.
- 🚫 Never hardcode API keys or secrets:
  - Use `.env` and `config.yaml` for configuration.
- 🧷 Handle edge cases gracefully:
  - missing data from quants-lab,
  - network errors,
  - temporarily unavailable exchanges or pools.
- 🔍 When the user asks you to “добавь”, “измени”, “поддержи” (e.g. новую биржу, сеть, фильтр):
  - infer the intent from this file,
  - modify or create the necessary modules **without** asking for redundant clarifications.

---

## XI. 🔬 Parser Pre-Testing Requirements

Before you rely on any parser or adapter for arbitrage logic, you **must test it**.

Testing can be done via:

- a dedicated module `/tests/parsers_test.py`,
- temporary scripts in a `playground/` directory,
- or similar.

### 1. CEX parsers via quants-lab

For each CEX you plan to use:

- Test fetching:
  - best bid / ask,
  - current mid price,
  - orderbook depth for a set of pairs,
  - available trading pairs list (if needed),
  - deposit/withdraw networks for the token (if quants-lab provides this).

- Log results like:

  ```text
  [OK] Binance spot: bid/ask loaded for VRA/USDT
  [OK] OKX spot: orderbook depth OK for VRA/USDT
  [OK] Gate.io spot: networks fetched for VRA
  ```

If data is missing or broken:

- investigate,
- fix adapters or config,
- or mark this CEX as unsupported until resolved.

### 2. DEX parsers

For each DEX / network combination you use:

- Test:
  - retrieving swap quotes for given token and volume,
  - computing effective prices on volume,
  - retrieving pool info and liquidity,
  - fetching gas estimates if available,
  - retrieving token contracts.

- Log something like:

  ```text
  [OK] UniswapV3 (Ethereum): quote for 1000 USDT → VRA OK
  [OK] UniswapV2 (BSC): pool depth sufficient for 5000$
  ```

### 3. Direction-wise checks

Before enabling each direction:

#### CEX–CEX

- Ensure you can fetch prices from both CEXes.
- Ensure `dif` is computed correctly.
- Ensure networks / chains for deposit/withdraw are known where relevant.
- For tokens used in examples, verify that the network indicated (e.g. BEP20) is indeed supported on both sides.

#### CEX–DEX

- Ensure:
  - DEX sell price is available,
  - CEX buy price is available,
  - `dif`, `prof`, `value` can be computed.
- Ensure network compatibility (CEX withdraw chain == DEX chain).

#### DEX–CEX

- Ensure:
  - DEX buy price (for spot buying) is available,
  - CEX sell price is available,
  - same computations work.

#### DEX–DEX

- Ensure:
  - you can fetch quotes or prices from both DEX legs,
  - tokens and pools are correctly identified,
  - you properly surface contract differences.

### 4. Contract logic tests

Verify that:

- Matching contracts → signals allowed + ✅ line shown.
- Mismatched contracts (CEX–DEX) → signals blocked.
- Missing CEX contract → signal allowed, but no ✅ line.

### 5. Amount/value/price sanity tests

For several tokens:

- Check that `amount` is consistent with:
  - `value` in USD,
  - `price` and liquidity.
- Check that `price` is actually the volume-weighted average price for the given `amount`.

### 6. Fallback rules

If a particular quants-lab parser:

- does not support some exchange, network or token,
- or frequently fails,

you must:

- either adapt/extend it,
- or disable that venue in configuration,
- and log it clearly so the user understands why a particular exchange/network is not used.

---

"Execution Restrictions"

Codex agent MUST NOT:

install packages

run pip commands

run unit tests requiring network

attempt to modify quants-lab to remove dependencies

attempt to vendor stubs for pandas

Codex MUST:

treat quants-lab and all dependencies as available in production

focus exclusively on generating code, not executing it

This file defines the **global behaviour** and expectations for the VS Code agent in this repository.  
Follow it as a system specification when writing, modifying and testing code.

Remember:  
🗣 **Общайся с пользователем по-русски.**  
💻 **Пиши код и комментарии по-английски.**
