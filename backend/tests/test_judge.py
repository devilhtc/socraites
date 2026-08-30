import asyncio
import json
from pathlib import Path

from socraites_api.judge import CodexAcpJudge, JudgeService
from socraites_api.models import JudgeStatus
from socraites_api.store import CourseStore


FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "courses"


def test_json_object_accepts_fenced_output() -> None:
    payload = CodexAcpJudge._json_object(
        """```json
        {"score": 1, "verdict": "correct", "feedback": "Good", "strengths": [], "improvements": []}
        ```"""
    )

    assert payload["verdict"] == "correct"


def test_tutor_agent_edits_only_staged_course_assets(tmp_path: Path, monkeypatch) -> None:
    store = CourseStore(FIXTURES_ROOT)
    course = store.course("test-course-a1b2c3")
    lesson = course.lessons[0]
    _, lesson_html = store.lesson_html(course.id, lesson.id)
    quiz = store.quiz(course.id, lesson.id)
    observed: dict[str, object] = {}

    async def complete(_self, prompt, *, workspace=None, mode="read-only"):
        assert workspace is not None
        observed["workspace"] = workspace
        observed["mode"] = mode
        observed["prompt"] = prompt
        lesson_path = workspace / "lesson.html"
        quiz_path = workspace / "quiz.json"
        lesson_path.write_text(lesson_path.read_text() + "\n<p>Added by the tutor.</p>\n")
        quiz_payload = json.loads(quiz_path.read_text())
        quiz_payload["title"] = "Expanded protocol boundary check"
        quiz_path.write_text(json.dumps(quiz_payload))
        return "```html\n<p>This deliberately oversized inline replacement must not reach chat.</p>\n```"

    service = JudgeService(tmp_path)
    monkeypatch.setattr(
        service,
        "status",
        lambda: JudgeStatus(
            configured_mode="codex-acp",
            active_mode="codex-acp",
            available=True,
            detail="available",
        ),
    )
    monkeypatch.setattr(CodexAcpJudge, "complete", complete)

    reply = asyncio.run(
        service.tutor(
            course.title,
            lesson.title,
            lesson_html,
            quiz,
            course.concepts,
            course.lessons,
            lesson.id,
            [],
            "Expand this chapter and quiz.",
        )
    )

    assert observed["mode"] == "agent"
    assert str(observed["workspace"]).startswith(str(tmp_path / ".socraites-agent"))
    assert "Teach Socratically in short turns" in str(observed["prompt"])
    assert "Never paste a complete lesson" in str(observed["prompt"])
    assert "COURSE CONCEPT INDEX" in str(observed["prompt"])
    assert "COURSE OUTLINE" in str(observed["prompt"])
    assert "AUTHORING REFERENCE" in str(observed["prompt"])
    assert "lean concrete scenario" in str(observed["prompt"])
    assert "Added by the tutor" in reply.lesson_html
    assert json.loads(reply.quiz_json)["title"] == "Expanded protocol boundary check"
    assert reply.text.startswith("Updated the lesson and quiz directly.")
    assert "```" not in reply.text
