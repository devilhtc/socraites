from socraites_api.judge import CodexAcpJudge


def test_json_object_accepts_fenced_output() -> None:
    payload = CodexAcpJudge._json_object(
        """```json
        {"score": 1, "verdict": "correct", "feedback": "Good", "strengths": [], "improvements": []}
        ```"""
    )

    assert payload["verdict"] == "correct"
