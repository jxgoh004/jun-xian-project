# Project: AI Economic Moat Analyzer

An AI-powered tool that evaluates the competitive durability ("economic moat") of any S&P 500 company across five classic Buffett/Morningstar dimensions. Rather than relying on static data, it spins up parallel AI agents that search the web in real time and return structured, evidence-backed scores.

## What it demonstrates

This project shows Jun Xian's ability to design a multi-agent AI workflow for a real analytical task — not just "call an LLM", but think carefully about prompt structure, parallel execution, partial failure handling, and synthesizing multiple independent analyses into a coherent verdict.

## How it works

The method follows Morningstar / Pat Dorsey: a moat needs one or two strong sources, not a high average across all five, and it only counts if it shows up as durable returns on capital. The models gather and judge evidence; the published score and label are computed in code (`moat_scoring.py`), so the same inputs always give the same rating.

1. **Financial fact sheet (code)** — built from the screener record: revenue growth, operating / net / free-cash-flow margins by year, approximate return on invested capital, return on equity. Return on invested capital = latest operating income × (1 − 21% tax) ÷ (equity + debt − cash). Cash is excluded because it is not capital at work in the business; it can remove at most half of equity + debt, so a cash-heavy balance sheet cannot push the return towards infinity. Every agent receives it and must not contradict it.

2. **5 Criterion Agents run in parallel** — each is a separate OpenAI Responses API call with the `web_search` tool enabled. They independently evaluate:
   - Brand Loyalty & Pricing Power
   - Barriers to Entry
   - Switching Costs
   - Network Effects
   - Economies of Scale

   Each agent returns a strict JSON object: `score` (0–10), `confidence` (high/medium/low), `trend` (strengthening/stable/weakening), `evidence` (3–5 bullet points with specific figures) and `risks` (2–3 bullets). `sources` are the pages the web search tool actually retrieved, taken from the API response rather than reported by the model.

3. **Skeptic Agent** — argues the bear case with its own web search and sets a haircut of 0–1.0 points.

4. **Rating (code)**
   - Source score = 0.6 × strongest criterion + 0.4 × second strongest
   - Minus the skeptic's haircut
   - Capped by the financial evidence: `strong` no cap, `adequate` or `unknown` 7.4 (so Wide needs strong financials), `weak` 5.9
   - `strong` = returns on capital ≥ 15%, margins positive every year and either stable (weakest year at least 70% of the best) or rising (ended above where they started and within 70% of their best year), free cash flow positive every year. The rising case exists because a wide spread caused by margins climbing, as at Nvidia, is not instability; it can also pass a cyclical company near its peak. `adequate` = returns ≥ 7% (≥ 10% ROE for financials) with at most one loss-making year. Banks and insurers are judged on ROE and net margin.
   - Moat trend follows the two strongest sources: `eroding` if either is weakening or the haircut is ≥ 0.7, `widening` if both are strengthening and the haircut is ≤ 0.3, otherwise `stable`. The skeptic does not set the trend, because it is prompted to find problems.
   - A failed criterion agent is excluded, not scored zero; with fewer than 3 successful agents no rating is published.

5. **Moat thresholds**
   - Wide: overall score ≥ 7.5
   - Wide-Narrow: ≥ 6.8
   - Narrow: ≥ 5.0
   - Narrow-None: ≥ 4.0
   - None: < 4.0

   The Wide and Wide-Narrow bars were lowered from 8.0 / 7.0 after the first full S&P 500 run, which put 4 of 503 stocks at Wide and two-thirds at Narrow. Stored ratings were relabelled in code from their saved criterion scores; no agent was re-run except the synthesizer, which rewrote the narrative for the 69 stocks whose label or score changed. Spread after the change, the rising-margin rule and the cash exclusion: 25 Wide, 155 Wide-Narrow, 295 Narrow, 26 Narrow-None, 2 None. For the cash exclusion, stored returns were scaled by the cash effect alone and the synthesizer rewrote every narrative that quoted the old figure.

6. **Synthesizer Agent** — a separate call with no web search is handed the fixed rating and writes the investment implication, key strength and key risk. It explains the rating; it cannot change it.

7. **Model and cost** — the criterion and skeptic agents run on `gpt-5.4-nano` and the synthesizer on `gpt-6.1-terra` (override with `MOAT_MODEL` / `MOAT_SYNTH_MODEL`), on the standard service tier. In a seven-stock test, running the agents on Terra roughly doubled the cost per stock (about $0.38 against $0.18) and produced the same label on six of seven, so Terra is kept for the narrative only. Flex (half-price tokens) can be switched on with `MOAT_SERVICE_TIER=flex`, but OpenAI refused every Flex call when tested, so it is off by default; a refused Flex call is retried on the standard tier. Each agent may make at most 3 web searches, because search fees ($10 per 1,000 calls) are the largest cost per stock.

8. **90-day cache and run order** — a rating is reused for 90 days. Each record stores `methodology`; ratings from an older methodology count as due. Due stocks are processed unrated first, then most undervalued first, and `--limit` caps how many one run processes.

Known limit: return on invested capital is approximated from four fiscal years of Yahoo data, and acquisition goodwill understates it for serial acquirers.

## Key files

```
economic-moat/
  moat_analyzer.py      # Async orchestrator: fact sheet, 5 criterion agents, skeptic, synthesizer
  moat_scoring.py       # Deterministic rules: fact sheet, financial evidence tier, score and label
  moat_prompts.py       # System prompts for the criterion agents, skeptic and synthesizer
  run_moat_analysis.py  # Batch runner for pre-generating analysis across S&P 500

docs/projects/moat/
  index.html            # This page — reads from data.json, no live API call needed
  data.json             # Pre-generated moat results (updated by batch runner)
```

## UI layout

The moat page is a **static viewer** — it reads from the pre-generated `data.json` snapshot and renders each company's analysis:

- **Hero section** — company name, ticker, sector/industry tags, moat verdict ring (SVG arc showing score 0–10), investment implication narrative
- **How this rating was reached** — the scoring arithmetic in one sentence, the financial evidence tier with its reasons, and the bear case
- **Criterion breakdown** — five score bars, each with evidence bullets and risk bullets
- **Sources** — URLs surfaced by the agents during web search

## Design choices worth noting

- Parallel execution is key: running 5 agents sequentially would take ~5× longer. `asyncio.gather()` fires all criterion calls at once
- Partial failure is handled gracefully — if one criterion agent errors, it is left out of the score rather than counted as zero, and the synthesizer still runs
- The page is intentionally static for the portfolio — no live API needed, loads instantly, and the pre-computed results demonstrate the output quality
- Shares the site-wide light neutral theme (`#edece7` ground, Host Grotesk, square corners, ink buttons); teal `#0d5c63` carries the radar and score bars, and status colour appears only on the verdict
