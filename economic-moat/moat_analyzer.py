"""
moat_analyzer.py — Economic Moat Analysis Engine

Orchestrates 5 parallel criterion agents + 1 synthesizer agent using the
OpenAI Responses API with the web_search tool (gpt-5.4-nano).

Usage (standalone test):
    python economic-moat/moat_analyzer.py AAPL "Apple Inc." Technology "Consumer Electronics"

Requires:
    OPENAI_API_KEY environment variable
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone

from openai import AsyncOpenAI

from moat_prompts import (
    CRITERION_KEYS,
    CRITERION_LABELS,
    CRITERION_PROMPTS,
    SYNTHESIZER_PROMPT,
)

MODEL = "gpt-5.4-nano"
TOOLS = [{"type": "web_search"}]


def _build_company_context(ticker: str, company_name: str, sector: str, industry: str) -> str:
    return (
        f"Company: {company_name} (ticker: {ticker})\n"
        f"Sector: {sector}\n"
        f"Industry: {industry}\n\n"
        "Analyse this specific company. Use web search to find current, factual evidence "
        "before scoring. Do not generalise — every data point should be company-specific."
    )


def _extract_json(text: str) -> dict:
    """Extract the first JSON object from a model response string."""
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"No JSON object found in response: {text[:200]}")
    return json.loads(match.group())


async def _run_criterion_agent(
    client: AsyncOpenAI,
    criterion_key: str,
    ticker: str,
    company_name: str,
    sector: str,
    industry: str,
) -> tuple[str, dict]:
    """Run a single criterion agent and return (criterion_key, result_dict)."""
    system_prompt = CRITERION_PROMPTS[criterion_key]
    user_message = _build_company_context(ticker, company_name, sector, industry)

    response = await client.responses.create(
        model=MODEL,
        tools=TOOLS,
        instructions=system_prompt,
        input=user_message,
    )

    raw_text = response.output_text
    result = _extract_json(raw_text)

    # Ensure required fields with safe defaults
    return criterion_key, {
        "score":      float(result.get("score", 0)),
        "confidence": result.get("confidence", "low"),
        "evidence":   result.get("evidence", []),
        "risks":      result.get("risks", []),
        "sources":    result.get("sources", []),
    }


async def _run_synthesizer(
    client: AsyncOpenAI,
    ticker: str,
    company_name: str,
    criteria_results: dict,
) -> dict:
    """Run the synthesizer agent over all 5 criterion results."""
    criteria_summary = json.dumps(
        {CRITERION_LABELS[k]: v for k, v in criteria_results.items()},
        indent=2,
    )
    user_message = (
        f"Company: {company_name} ({ticker})\n\n"
        f"Criterion Analysis Results:\n{criteria_summary}"
    )

    response = await client.responses.create(
        model=MODEL,
        tools=TOOLS,
        instructions=SYNTHESIZER_PROMPT,
        input=user_message,
    )

    raw_text = response.output_text
    result = _extract_json(raw_text)

    scores = [v["score"] for v in criteria_results.values()]
    fallback_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    overall_score = float(result.get("overall_score", fallback_score))

    if overall_score >= 7.0:
        moat = "Wide"
    elif overall_score >= 4.0:
        moat = "Narrow"
    else:
        moat = "None"

    return {
        "overall_moat":           result.get("overall_moat", moat),
        "overall_score":          overall_score,
        "investment_implication": result.get("investment_implication", ""),
        "key_strength":           result.get("key_strength", ""),
        "key_risk":               result.get("key_risk", ""),
    }


async def analyze_company(
    ticker: str,
    company_name: str,
    sector: str = "N/A",
    industry: str = "N/A",
    api_key: str | None = None,
) -> dict:
    """
    Full moat analysis for one company.

    Returns a dict matching the data.json stock schema:
    {
        ticker, company_name, overall_moat, overall_score,
        investment_implication, key_strength, key_risk,
        criteria: { brand_loyalty, barriers_to_entry, switching_costs,
                    network_effects, economies_of_scale },
        analyzed_at
    }
    """
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise EnvironmentError("OPENAI_API_KEY environment variable not set.")

    client = AsyncOpenAI(api_key=key)

    # Run all 5 criterion agents in parallel
    tasks = [
        _run_criterion_agent(client, ck, ticker, company_name, sector, industry)
        for ck in CRITERION_KEYS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    criteria_results: dict = {}
    for item in results:
        if isinstance(item, Exception):
            # Partial failure — log and use a zero-score placeholder
            print(f"  [warn] criterion agent error: {item}", file=sys.stderr)
            continue
        criterion_key, criterion_data = item
        criteria_results[criterion_key] = criterion_data

    # Fill any missing criteria with zero-score placeholders
    for ck in CRITERION_KEYS:
        if ck not in criteria_results:
            criteria_results[ck] = {
                "score": 0.0, "confidence": "low",
                "evidence": [], "risks": [], "sources": [],
            }

    # Synthesizer
    synthesis = await _run_synthesizer(client, ticker, company_name, criteria_results)

    return {
        "ticker":                 ticker,
        "company_name":           company_name,
        "overall_moat":           synthesis["overall_moat"],
        "overall_score":          synthesis["overall_score"],
        "investment_implication": synthesis["investment_implication"],
        "key_strength":           synthesis["key_strength"],
        "key_risk":               synthesis["key_risk"],
        "criteria":               criteria_results,
        "analyzed_at":            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ---------------------------------------------------------------------------
# CLI test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python moat_analyzer.py <TICKER> <Company Name> [Sector] [Industry]")
        sys.exit(1)

    ticker_arg      = sys.argv[1].upper()
    company_arg     = sys.argv[2]
    sector_arg      = sys.argv[3] if len(sys.argv) > 3 else "N/A"
    industry_arg    = sys.argv[4] if len(sys.argv) > 4 else "N/A"

    result = asyncio.run(
        analyze_company(ticker_arg, company_arg, sector_arg, industry_arg)
    )
    print(json.dumps(result, indent=2))
