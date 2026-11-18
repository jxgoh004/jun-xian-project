"""
moat_analyzer.py — Economic Moat Analysis Engine

Pipeline for one company (OpenAI Responses API):

  1. Fact sheet        reported financials from the screener record (code)
  2. 5 criterion agents, in parallel, each with web search
  3. Skeptic agent     argues the bear case and sets a haircut
  4. Rating            strongest sources − haircut, capped by financials;
                       trend from the direction of the strongest sources (code)
  5. Synthesizer       writes the narrative for the rating it is given

Usage (standalone test, ticker must exist in the screener data.json):
    python economic-moat/moat_analyzer.py AAPL

Requires:
    OPENAI_API_KEY environment variable

Optional:
    MOAT_MODEL        model for criterion and skeptic agents (default gpt-5.4-nano)
    MOAT_SYNTH_MODEL  model for the synthesizer             (default gpt-6.1-terra)
    MOAT_SERVICE_TIER "default" (standard) or "flex" (half-price tokens when OpenAI
                      has capacity; refused calls are retried on the standard tier)
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
    SKEPTIC_PROMPT,
    SYNTHESIZER_PROMPT,
)
from moat_scoring import (
    METHODOLOGY_VERSION,
    assess_financials,
    build_fact_sheet,
    compute_rating,
    format_fact_sheet,
)

# Agents on nano, summary on Terra: in a seven-stock test Terra agents cost about
# twice as much and gave the same label on six of seven.
MODEL = os.environ.get("MOAT_MODEL", "gpt-5.4-nano")
SYNTH_MODEL = os.environ.get("MOAT_SYNTH_MODEL", "gpt-6.1-terra")
# Flex was refused on every call when tested (Nov 2026), so standard is the default.
SERVICE_TIER = os.environ.get("MOAT_SERVICE_TIER", "default")
# "low" context keeps the search results fed back to the model small; those
# result tokens are most of the input bill.
TOOLS = [{"type": "web_search", "search_context_size": "low"}]
MAX_SEARCHES = 3          # web searches allowed per agent — the main cost driver
MAX_SOURCES = 5

VALID_CONFIDENCE = {"high", "medium", "low"}
VALID_CRITERION_TREND = {"strengthening", "stable", "weakening"}
INCLUDE = ["web_search_call.action.sources"]   # return the pages each search retrieved


def _company_context(stock: dict, fact_sheet_text: str) -> str:
    return (
        f"Company: {stock.get('company_name', stock['ticker'])} (ticker: {stock['ticker']})\n"
        f"Sector: {stock.get('sector', 'N/A')}\n"
        f"Industry: {stock.get('industry', 'N/A')}\n\n"
        f"{fact_sheet_text}\n\n"
        "Analyse this specific company. Do not generalise — every data point should be "
        "company-specific."
    )


def _extract_json(text: str) -> dict:
    """Extract the first JSON object from a model response string."""
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"No JSON object found in response: {text[:200]}")
    return json.loads(match.group())


def _field(obj, name):
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def _cited_urls(response) -> list[str]:
    """
    URLs the web search tool actually returned, without duplicates.

    Inline citations come first; because the agents answer in bare JSON they
    rarely cite inline, so the pages each search call retrieved fill the rest.
    """
    cited: list[str] = []
    retrieved: list[str] = []
    for item in _field(response, "output") or []:
        for part in _field(item, "content") or []:
            for note in _field(part, "annotations") or []:
                cited.append(_field(note, "url"))
        for source in _field(_field(item, "action"), "sources") or []:
            retrieved.append(_field(source, "url"))
    urls: list[str] = []
    for url in cited + retrieved:
        if url and url not in urls:
            urls.append(url)
    return urls[:MAX_SOURCES]


def _add_usage(usage: dict, response) -> None:
    used = getattr(response, "usage", None)
    usage["input_tokens"] += getattr(used, "input_tokens", 0) or 0
    usage["output_tokens"] += getattr(used, "output_tokens", 0) or 0
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", "") != "web_search_call":
            continue
        # A web_search_call is either a search or a follow-up page open / find.
        kind = getattr(getattr(item, "action", None), "type", "search")
        usage["web_searches" if kind == "search" else "page_opens"] += 1


def _one_of(value, allowed: set, default: str) -> str:
    return value if value in allowed else default


_INLINE_CITATION = re.compile(r"\s*\(?\[[^\]]*\]\(https?://[^)\s]+\)\)?")


def clean_text(value):
    """Strip inline markdown citations; sources are stored separately as URLs."""
    if isinstance(value, list):
        return [clean_text(v) for v in value]
    if not isinstance(value, str):
        return value
    return _INLINE_CITATION.sub("", value).strip()


async def _create(client: AsyncOpenAI, usage: dict, **params):
    """
    Call the Responses API on the configured service tier.

    Flex is half price but can be refused when capacity is short; a refused
    or failed flex call is retried once on the standard tier.
    """
    if SERVICE_TIER != "default":
        try:
            response = await client.responses.create(service_tier=SERVICE_TIER, **params)
            _add_usage(usage, response)
            return response
        except Exception as exc:  # noqa: BLE001
            usage["standard_tier_retries"] += 1
            print(f"  [warn] {SERVICE_TIER} tier failed, retrying on standard: {exc}", file=sys.stderr)
    response = await client.responses.create(**params)
    _add_usage(usage, response)
    return response


async def _run_criterion_agent(
    client: AsyncOpenAI, criterion_key: str, context: str, usage: dict,
) -> tuple[str, dict]:
    """Run a single criterion agent and return (criterion_key, result_dict)."""
    response = await _create(
        client, usage,
        model=MODEL,
        tools=TOOLS,
        max_tool_calls=MAX_SEARCHES,
        include=INCLUDE,
        instructions=CRITERION_PROMPTS[criterion_key],
        input=context,
    )
    result = _extract_json(response.output_text)

    return criterion_key, {
        "score":      max(0.0, min(10.0, float(result["score"]))),
        "confidence": _one_of(result.get("confidence"), VALID_CONFIDENCE, "low"),
        "trend":      _one_of(result.get("trend"), VALID_CRITERION_TREND, "stable"),
        "evidence":   clean_text(result.get("evidence", [])),
        "risks":      clean_text(result.get("risks", [])),
        "sources":    _cited_urls(response),
    }


async def _run_skeptic(
    client: AsyncOpenAI, context: str, criteria_summary: str, usage: dict,
) -> dict:
    """Argue the bear case. A failure here means no haircut, not no rating."""
    try:
        response = await _create(
            client, usage,
            model=MODEL,
            tools=TOOLS,
            max_tool_calls=MAX_SEARCHES,
            include=INCLUDE,
            instructions=SKEPTIC_PROMPT,
            input=f"{context}\n\nCriterion analyses:\n{criteria_summary}",
        )
        result = _extract_json(response.output_text)
        return {
            "haircut":    float(result.get("haircut", 0.0)),
            "bear_case":  clean_text(result.get("bear_case", [])),
            "sources":    _cited_urls(response),
        }
    except Exception as exc:  # noqa: BLE001 — any failure degrades to "no bear case"
        print(f"  [warn] skeptic agent error: {exc}", file=sys.stderr)
        return {"haircut": 0.0, "bear_case": [], "sources": []}


async def _run_synthesizer(client: AsyncOpenAI, material: str, usage: dict) -> dict:
    """Write the narrative. Falls back to the agent model if SYNTH_MODEL is unavailable."""
    last_error: Exception | None = None
    for model in dict.fromkeys((SYNTH_MODEL, MODEL)):
        try:
            response = await _create(
                client, usage, model=model, instructions=SYNTHESIZER_PROMPT, input=material,
            )
            result = _extract_json(response.output_text)
            return {
                "investment_implication": clean_text(result.get("investment_implication", "")),
                "key_strength":           clean_text(result.get("key_strength", "")),
                "key_risk":               clean_text(result.get("key_risk", "")),
                "model":                  model,
            }
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"  [warn] synthesizer failed on {model}: {exc}", file=sys.stderr)
    raise RuntimeError(f"synthesizer failed: {last_error}")


async def analyze_company(stock: dict, api_key: str | None = None) -> dict:
    """
    Full moat analysis for one screener record.

    Raises if too few criterion agents succeed to publish a rating.
    Returns a dict matching the moat data.json stock schema.
    """
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise EnvironmentError("OPENAI_API_KEY environment variable not set.")

    client = AsyncOpenAI(api_key=key)
    usage = {"input_tokens": 0, "output_tokens": 0, "web_searches": 0, "page_opens": 0,
             "standard_tier_retries": 0}

    fact_sheet = build_fact_sheet(stock)
    financials = assess_financials(fact_sheet)
    context = _company_context(stock, format_fact_sheet(fact_sheet))

    # 5 criterion agents in parallel. A failed agent is excluded from the
    # rating (score None) rather than counted as a zero.
    results = await asyncio.gather(
        *(_run_criterion_agent(client, ck, context, usage) for ck in CRITERION_KEYS),
        return_exceptions=True,
    )
    criteria: dict = {}
    for ck, item in zip(CRITERION_KEYS, results):
        if isinstance(item, Exception):
            print(f"  [warn] {ck} agent error: {item}", file=sys.stderr)
            criteria[ck] = {
                "score": None, "failed": True, "confidence": "low", "trend": "stable",
                "evidence": [], "risks": [], "sources": [],
            }
        else:
            criteria[ck] = item[1]

    criteria_summary = json.dumps(
        {
            CRITERION_LABELS[k]: {f: v[f] for f in ("score", "confidence", "trend", "evidence", "risks")}
            for k, v in criteria.items() if v["score"] is not None
        },
        indent=2,
    )

    skeptic = await _run_skeptic(client, context, criteria_summary, usage)
    rating = compute_rating(criteria, financials, skeptic["haircut"])

    material = (
        f"{context}\n\n"
        f"Criterion analyses:\n{criteria_summary}\n\n"
        f"Bear case:\n{json.dumps(skeptic['bear_case'], indent=2)}\n\n"
        "Final rating (fixed — explain it, do not change it):\n"
        + json.dumps(
            {
                "overall_moat":       rating["overall_moat"],
                "overall_score":      rating["overall_score"],
                "moat_trend":         rating["moat_trend"],
                "strongest_sources":  [CRITERION_LABELS[k] for k in rating["scoring"]["top_sources"]],
                "financial_evidence": financials,
                "capped_by_financial_evidence": rating["scoring"]["capped"],
            },
            indent=2,
        )
    )
    synthesis = await _run_synthesizer(client, material, usage)

    return {
        "ticker":                 stock["ticker"],
        "company_name":           stock.get("company_name", stock["ticker"]),
        "overall_moat":           rating["overall_moat"],
        "overall_score":          rating["overall_score"],
        "moat_trend":             rating["moat_trend"],
        "investment_implication": synthesis["investment_implication"],
        "key_strength":           synthesis["key_strength"],
        "key_risk":               synthesis["key_risk"],
        "criteria":               criteria,
        "bear_case":              skeptic["bear_case"],
        "bear_case_sources":      skeptic["sources"],
        "financial_evidence":     {**financials, "metrics": fact_sheet},
        "scoring":                rating["scoring"],
        "methodology":            METHODOLOGY_VERSION,
        "models":                 {"agents": MODEL, "synthesizer": synthesis["model"]},
        "usage":                  usage,
        "analyzed_at":            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ---------------------------------------------------------------------------
# CLI test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python moat_analyzer.py <TICKER>")
        sys.exit(1)

    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(_root, "docs", "projects", "screener", "data.json"), encoding="utf-8") as fh:
        _stocks = {s["ticker"]: s for s in json.load(fh).get("stocks", [])}

    _ticker = sys.argv[1].upper()
    if _ticker not in _stocks:
        print(f"{_ticker} not found in screener data.json")
        sys.exit(1)

    print(json.dumps(asyncio.run(analyze_company(_stocks[_ticker])), indent=2))
