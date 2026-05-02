# Project: AI Economic Moat Analyzer

An AI-powered tool that evaluates the competitive durability ("economic moat") of any S&P 500 company across five classic Buffett/Morningstar dimensions. Rather than relying on static data, it spins up parallel AI agents that search the web in real time and return structured, evidence-backed scores.

## What it demonstrates

This project shows Jun Xian's ability to design a multi-agent AI workflow for a real analytical task — not just "call an LLM", but think carefully about prompt structure, parallel execution, partial failure handling, and synthesizing multiple independent analyses into a coherent verdict.

## How it works

1. **5 Criterion Agents run in parallel** — each is a separate OpenAI Responses API call with the `web_search` tool enabled. They independently evaluate:
   - Brand Loyalty & Pricing Power
   - Barriers to Entry
   - Switching Costs
   - Network Effects
   - Economies of Scale

   Each agent returns a strict JSON object: `score` (0–10), `confidence` (high/medium/low), `evidence` (3–5 bullet points with specific figures), `risks` (2–3 bullets), and `sources` (URLs consulted).

2. **Synthesizer Agent** — after all 5 criterion results are gathered, a separate agent reviews them holistically and produces:
   - Overall moat rating: Wide / Narrow / None
   - Overall score (weighted average)
   - Investment implication (2–3 sentence narrative)
   - Key strength and key risk

3. **Moat thresholds**
   - Wide: overall score ≥ 8.0
   - Wide-Narrow: ≥ 7.0
   - Narrow: ≥ 5.0
   - Narrow-None: ≥ 4.0
   - None: < 4.0

4. **30-day cache** — results are cached per ticker in `data.json` to avoid redundant API calls when re-visiting the same company

## Key files

```
economic-moat/
  moat_analyzer.py      # Async orchestrator: 5 parallel criterion agents + synthesizer
  moat_prompts.py       # System prompts for each criterion agent + synthesizer
  run_moat_analysis.py  # Batch runner for pre-generating analysis across S&P 500

docs/projects/moat/
  index.html            # This page — reads from data.json, no live API call needed
  data.json             # Pre-generated moat results (updated by batch runner)
```

## UI layout

The moat page is a **static viewer** — it reads from the pre-generated `data.json` snapshot and renders each company's analysis:

- **Hero section** — company name, ticker, sector/industry tags, moat verdict ring (SVG arc showing score 0–10), investment implication narrative
- **Criterion breakdown** — five score bars, each with evidence bullets and risk bullets
- **Sources** — URLs surfaced by the agents during web search

## Design choices worth noting

- Parallel execution is key: running 5 agents sequentially would take ~5× longer. `asyncio.gather()` fires all criterion calls at once
- Partial failure is handled gracefully — if one criterion agent errors, it's filled with a zero-score placeholder and the synthesizer still runs
- The page is intentionally static for the portfolio — no live API needed, loads instantly, and the pre-computed results demonstrate the output quality
- The dark blue-on-black theme with dot-grid background (`#080c12`, `Syne` display font) distinguishes this visually from the calculator, signalling a different tool with a different analytical purpose
