import json
from pathlib import Path

from fastapi.testclient import TestClient

from socraites_api.judge import JudgeService, TutorReply
from socraites_api.main import create_app
from socraites_api.models import ChoiceOption, SingleChoiceQuestion


FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "courses"


def make_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("SOCRAITES_JUDGE", "local")
    app = create_app(
        courses_root=FIXTURES_ROOT,
        progress_root=tmp_path / "progress",
        mount_frontend=False,
    )
    return TestClient(app)


def test_rendered_lesson_uses_shared_theme_and_csp(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)

    response = client.get("/render/courses/test-course-a1b2c3/lessons/boundary?theme=light")

    assert response.status_code == 200
    assert '<html lang="en" data-theme="light">' in response.text
    assert "sandbox" in response.headers["content-security-policy"]
    assert "sandbox allow-same-origin" not in response.headers["content-security-policy"]
    assert "script-src 'none'" in response.headers["content-security-policy"]
    assert "body { height:100%; margin:0; overflow:auto;" in response.text
    assert "article { width:min(100%,920px); margin:0 auto; padding:48px 32px 80px;" in response.text


def test_attempt_is_graded_and_written_to_files(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)

    draft_response = client.put(
        "/api/courses/test-course-a1b2c3/lessons/boundary/draft",
        json={"answers": {"boundary-owner": "conversation", "boundary-explain": "A saved draft"}},
    )
    assert draft_response.status_code == 200
    assert draft_response.json()["lessons"]["boundary"]["answers"]["boundary-explain"] == "A saved draft"

    response = client.post(
        "/api/courses/test-course-a1b2c3/lessons/boundary/attempts",
        json={
            "answers": {
                "boundary-owner": "conversation",
                "boundary-explain": "ACP coordinates the editor and agent conversation while MCP lets the agent call external tools and data.",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["verdict"] == "correct"
    assert payload["results"][1]["judge"] == "local-rubric-preview"
    assert payload["answers"]["boundary-owner"] == "conversation"
    assert (tmp_path / "progress" / "local" / "test-course-a1b2c3" / "progress.json").is_file()

    course_response = client.get("/api/courses/test-course-a1b2c3")
    assert course_response.status_code == 200
    saved_progress = course_response.json()["progress"]["lessons"]["boundary"]
    assert saved_progress["attempts"] == 1
    assert saved_progress["best_score"] == payload["score"]

    restored = make_client(tmp_path, monkeypatch).get("/api/courses/test-course-a1b2c3/workspace")
    assert restored.status_code == 200
    restored_work = restored.json()["lessons"]["boundary"]
    assert restored_work["status"] == "graded"
    assert restored_work["answers"] == payload["answers"]
    assert restored_work["latest_attempt"]["results"] == payload["results"]

    event_files = tuple((tmp_path / "progress" / "local" / "test-course-a1b2c3" / "interactions").glob("*.json"))
    event_kinds = {json.loads(path.read_text())["kind"] for path in event_files}
    assert {"draft_saved", "grading_started", "grading_completed"} <= event_kinds


def test_navigation_and_draft_survive_a_fresh_app_instance(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    navigation = client.put(
        "/api/courses/test-course-a1b2c3/workspace",
        json={"active_lesson_id": "boundary", "active_phase": "quiz"},
    )
    assert navigation.status_code == 200

    draft = client.put(
        "/api/courses/test-course-a1b2c3/lessons/boundary/draft",
        json={"answers": {"boundary-explain": "My unfinished explanation"}},
    )
    assert draft.status_code == 200

    restored = make_client(tmp_path, monkeypatch).get("/api/courses/test-course-a1b2c3/workspace")
    payload = restored.json()
    assert payload["active_lesson_id"] == "boundary"
    assert payload["active_phase"] == "quiz"
    assert payload["lessons"]["boundary"]["answers"]["boundary-explain"] == "My unfinished explanation"


def test_quiz_response_does_not_leak_answers(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)

    response = client.get("/api/courses/test-course-a1b2c3/lessons/boundary/quiz")

    assert response.status_code == 200
    text = response.text
    assert "correct_option_ids" not in text
    assert "correct_order" not in text
    assert "reference_answer" not in text


def test_generated_questions_are_private_and_survive_restart(tmp_path: Path, monkeypatch) -> None:
    async def generate_questions(*_args, **_kwargs):
        return [
            SingleChoiceQuestion(
                id=f"generated-test-{index}",
                type="single_choice",
                prompt=f"Generated question {index}?",
                points=3.0,
                options=[
                    ChoiceOption(id="yes", label="Yes"),
                    ChoiceOption(id="no", label="No"),
                ],
                correct_option_ids=["yes"],
                explanation="Yes is correct for this generated test question.",
            )
            for index in range(1, 4)
        ]

    monkeypatch.setattr(JudgeService, "generate_questions", generate_questions)
    client = make_client(tmp_path, monkeypatch)

    generated = client.post("/api/courses/test-course-a1b2c3/lessons/boundary/questions/generate")

    assert generated.status_code == 200
    payload = generated.json()
    assert payload["authored_question_count"] == 5
    assert payload["generated_question_count"] == 3
    assert len(payload["questions"]) == 8
    assert "correct_option_ids" not in generated.text

    restored = make_client(tmp_path, monkeypatch).get("/api/courses/test-course-a1b2c3/lessons/boundary/quiz")
    assert restored.status_code == 200
    assert restored.json()["generated_question_count"] == 3
    assert len(restored.json()["questions"]) == 8
    assert len(tuple((tmp_path / "progress" / "local" / "test-course-a1b2c3" / "generated" / "boundary").glob("*.json"))) == 1

    event_files = tuple((tmp_path / "progress" / "local" / "test-course-a1b2c3" / "interactions").glob("*.json"))
    event_kinds = {json.loads(path.read_text())["kind"] for path in event_files}
    assert "questions_generated" in event_kinds


def test_tutor_conversation_uses_chapter_context_and_survives_restart(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def tutor(_self, course_title, lesson_title, lesson_html, quiz, history, user_text):
        captured.update({
            "course_title": course_title,
            "lesson_title": lesson_title,
            "lesson_html": lesson_html,
            "quiz": quiz,
            "history": history,
            "user_text": user_text,
        })
        return TutorReply(
            text="Think of ACP as the conversation boundary between an editor and an agent.",
            lesson_html=lesson_html,
            quiz_json=quiz.model_dump_json(indent=2),
        )

    monkeypatch.setattr(JudgeService, "tutor", tutor)
    client = make_client(tmp_path, monkeypatch)
    empty = client.get("/api/courses/test-course-a1b2c3/lessons/boundary/tutor")
    assert empty.status_code == 200
    assert empty.json()["conversation"] is None

    response = client.post(
        "/api/courses/test-course-a1b2c3/lessons/boundary/tutor/messages",
        json={"text": "What boundary does ACP create?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation"]["turns"][0]["status"] == "completed"
    assert payload["conversation"]["turns"][0]["assistant_text"].startswith("Think of ACP")
    assert captured["course_title"] == "Test Course"
    assert captured["lesson_title"] == "Protocol boundary"
    assert "A protocol boundary separates" in str(captured["lesson_html"])
    assert captured["user_text"] == "What boundary does ACP create?"

    restored = make_client(tmp_path, monkeypatch).get("/api/courses/test-course-a1b2c3/lessons/boundary/tutor")
    assert restored.status_code == 200
    assert restored.json()["conversation"]["turns"] == payload["conversation"]["turns"]

    new_chat = client.post("/api/courses/test-course-a1b2c3/lessons/boundary/tutor/conversations")
    assert new_chat.status_code == 200
    assert new_chat.json()["conversation"]["turns"] == []
    assert len(new_chat.json()["conversations"]) == 2

    event_files = tuple((tmp_path / "progress" / "local" / "test-course-a1b2c3" / "interactions").glob("*.json"))
    event_kinds = {json.loads(path.read_text())["kind"] for path in event_files}
    assert {"tutor_conversation_started", "tutor_turn_started", "tutor_turn_completed"} <= event_kinds
