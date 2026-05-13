from sentinel_pr_review.orchestration.llm_specialists import _extract_json_payload, _parse_findings


def test_parse_specialist_json_from_code_fence() -> None:
    payload = _extract_json_payload(
        '```json\n{"findings":[{"id":"SEC-001","severity":"High","title":"Secret leak","evidence":"api_key","confidence":0.9}]}\n```'
    )
    findings = _parse_findings(payload, "security", 0.65)
    assert findings[0].title == "Secret leak"
    assert findings[0].agent == "security"
