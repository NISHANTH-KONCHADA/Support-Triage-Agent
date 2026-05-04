"""
LLM-backed ticket triage for the Support Triage Agent project.
"""

import json
import os
import re
import time
from typing import Dict

from groq import Groq

from retriever import get_corpus


def _get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "\nGROQ_API_KEY is not set.\n"
            "  1. Get a free key at: https://console.groq.com\n"
            "  2. Windows: set GROQ_API_KEY=your-key-here\n"
            "  3. macOS / Linux: export GROQ_API_KEY=your-key-here\n"
        )
    return Groq(api_key=api_key)


SYSTEM_PROMPT = """You are a senior support triage agent for a multi-product helpdesk.
You handle tickets for three products: HackerRank, Claude (Anthropic), and Visa.

Rules:
1. Use ONLY the provided support corpus excerpts - do not use outside knowledge.
2. Do NOT invent policies, steps, or facts not in the corpus.
3. Escalate when: fraud/billing risk, account suspension, security breach, legal issues,
   no relevant corpus info, or any high-stakes situation.

request_type values:
- "product_issue"   : something that should work but doesn't
- "feature_request" : user wants something new
- "bug"             : reproducible defect
- "invalid"         : spam, gibberish, completely out of scope

Respond ONLY with a valid JSON object - no markdown fences, no extra text:
{
  "status": "replied" | "escalated",
  "product_area": "<e.g. Billing, Assessments, Account Access, Fraud, API, General>",
  "response": "<polite, corpus-grounded user-facing reply>",
  "justification": "<1-2 sentences on the routing/answer decision>",
  "request_type": "product_issue" | "feature_request" | "bug" | "invalid"
}"""

USER_PROMPT_TEMPLATE = """SUPPORT TICKET
Company: {company}
Subject: {subject}
Issue: {issue}

CORPUS EXCERPTS (answer based on these only)
{context}

Reply with the JSON object only."""

MODEL = "llama-3.3-70b-versatile"

_client = None


def triage(issue: str, subject: str, company: str, *, retries: int = 3) -> Dict[str, str]:
    global _client
    if _client is None:
        _client = _get_client()

    corpus = get_corpus()
    query = f"{subject} {issue}"[:500]

    chunks = corpus.retrieve(query, company=_normalize_company(company), top_k=5)
    if not chunks:
        chunks = corpus.retrieve(query, company=None, top_k=5)

    context = "\n\n".join(
        f"[{i}] ({source_company})\n{text[:450]}"
        for i, (text, source_company, _) in enumerate(chunks, 1)
    ) or "(No relevant corpus material found.)"

    user_message = USER_PROMPT_TEMPLATE.format(
        company=company or "Unknown",
        subject=subject or "(no subject)",
        issue=(issue or "(no issue)")[:600],
        context=context,
    )

    for attempt in range(retries):
        try:
            response = _client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.0,
                max_tokens=600,
            )
            raw = response.choices[0].message.content.strip()
            result = _parse_json(raw)
            _validate(result)
            return result
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"  [parse error] {exc}", flush=True)
            if attempt < retries - 1:
                time.sleep(1)
                continue
            return _safe_fallback(f"parse error: {exc}")
        except Exception as exc:
            print(f"  [API error] {type(exc).__name__}: {exc}", flush=True)
            err = str(exc).lower()
            if "429" in err or "rate" in err or "quota" in err:
                wait_seconds = 15 * (attempt + 1)
                print(f"  [rate limit] waiting {wait_seconds}s...", flush=True)
                time.sleep(wait_seconds)
                continue
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return _safe_fallback(str(exc))

    return _safe_fallback("max retries exceeded")


def _normalize_company(company: str):
    if not company:
        return None
    return {
        "hackerrank": "HackerRank",
        "claude": "Claude",
        "visa": "Visa",
    }.get(company.strip().lower())


def _parse_json(raw: str) -> Dict:
    cleaned = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.MULTILINE)
    cleaned = re.sub(r"\n?```$", "", cleaned, flags=re.MULTILINE)
    return json.loads(cleaned.strip())


def _validate(result: Dict) -> None:
    required = {"status", "product_area", "response", "justification", "request_type"}
    missing = required - result.keys()
    if missing:
        raise ValueError(f"Missing keys: {missing}")
    if result["status"] not in {"replied", "escalated"}:
        raise ValueError(f"Bad status: {result['status']}")
    if result["request_type"] not in {"product_issue", "feature_request", "bug", "invalid"}:
        raise ValueError(f"Bad request_type: {result['request_type']}")


def _safe_fallback(reason: str) -> Dict[str, str]:
    return {
        "status": "escalated",
        "product_area": "General",
        "response": (
            "We've received your request and have escalated it to our support team. "
            "A human agent will follow up with you shortly."
        ),
        "justification": f"Escalated due to processing error: {reason[:120]}",
        "request_type": "product_issue",
    }
