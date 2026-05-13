from __future__ import annotations

import json
import re
from typing import Any

from sentinel_pr_review.llm_client import LLMClient
from sentinel_pr_review.models import Finding
from sentinel_pr_review.orchestration.state import ReviewState
from sentinel_pr_review.prompt_loader import load_prompt


def _extract_json_payload(text: str) -> dict[str, Any]:
    if not text.strip():
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
    return {}


def _parse_findings(payload: dict[str, Any], agent: str, threshold: float) -> list[Finding]:
    findings: list[Finding] = []
    for index, item in enumerate(payload.get("findings", []), start=1):
        confidence = float(item.get("confidence", 0.0))
        findings.append(
            Finding(
                id=str(item.get("id", f"{agent[:3].upper()}-LLM-{index:03d}")),
                agent=agent,
                severity=item.get("severity", "Medium"),
                title=item.get("title", "LLM finding"),
                file=item.get("file"),
                line_start=item.get("line_start"),
                line_end=item.get("line_end"),
                evidence=item.get("evidence", ""),
                confidence=confidence,
                needs_human_review=bool(item.get("needs_human_review", confidence < threshold)),
            )
        )
    return findings


def _merge_findings(primary: list[Finding], secondary: list[Finding]) -> list[Finding]:
    merged = list(primary)
    seen = {(item.title, item.file, item.line_start) for item in primary}
    for finding in secondary:
        key = (finding.title, finding.file, finding.line_start)
        if key in seen:
            continue
        merged.append(finding)
        seen.add(key)
    return merged


def augment_with_llm(agent: str, state: ReviewState, heuristic_findings: list[Finding]) -> tuple[list[Finding], int]:
    settings = state["settings"]
    client = LLMClient(settings)
    if client._client is None:
        return heuristic_findings, 0

    budget = settings.budget_for(agent)
    diff_excerpt = state["context"].text[: budget * 4]
    user_prompt = (
        f"Title: {state['request'].title}\n"
        f"Description: {state['request'].description}\n"
        f"Confidence threshold: {state['request'].confidence_threshold}\n"
        f"Diff:\n{diff_excerpt}"
    )
    text, usage = client.complete(
        load_prompt(agent),
        user_prompt,
        settings.specialist_model,
        max_tokens=min(1200, budget),
    )
    payload = _extract_json_payload(text)
    llm_findings = _parse_findings(payload, agent, state["request"].confidence_threshold)
    return _merge_findings(heuristic_findings, llm_findings), usage


def coordinator_summary(state: ReviewState, findings: list[Finding]) -> tuple[str, int]:
    settings = state["settings"]
    client = LLMClient(settings)
    if client._client is None:
        return f"{state['request'].title} modifies {len(state['context'].files)} file(s).", 0

    budget = settings.budget_for("coordinator")
    user_prompt = json.dumps(
        {
            "title": state["request"].title,
            "description": state["request"].description,
            "findings": [finding.model_dump() for finding in findings],
            "clarifications": state["clarifications"],
        },
        indent=2,
    )
    text, usage = client.complete(
        load_prompt("coordinator"),
        user_prompt,
        settings.coordinator_model,
        max_tokens=min(1500, budget),
    )
    payload = _extract_json_payload(text)
    summary = payload.get("pr_summary") or text.strip()
    if not summary:
        summary = f"{state['request'].title} modifies {len(state['context'].files)} file(s)."
    return summary, usage
