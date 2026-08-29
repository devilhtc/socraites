from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .judge import JudgeService, JudgeUnavailable
from .mermaid import MermaidRenderer
from .models import (
    AttemptRequest,
    AttemptResult,
    CourseView,
    DraftRequest,
    JudgeResult,
    JudgeVerdict,
    MultipleChoiceQuestion,
    OrderingQuestion,
    PublicQuiz,
    QuestionResult,
    Quiz,
    SingleChoiceQuestion,
    TutorMessageRequest,
    TutorView,
    WorkspaceNavigationRequest,
    WorkspaceView,
)
from .store import CourseStore, InvalidDataError, NotFoundError, ProgressStore

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT_ROOT / "data"

LESSON_CSP = "; ".join(
    (
        "sandbox",
        "default-src 'none'",
        "style-src 'unsafe-inline'",
        "img-src data:",
        "script-src 'none'",
        "connect-src 'none'",
        "font-src 'none'",
        "media-src 'none'",
        "object-src 'none'",
        "frame-src 'none'",
        "form-action 'none'",
        "base-uri 'none'",
        "frame-ancestors 'self'",
    )
)

LESSON_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Content-Security-Policy": LESSON_CSP,
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}

LESSON_SHELL = """<!doctype html>
<html lang="en" data-theme="{{THEME}}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Socraites lesson</title>
  <style>
    :root { color-scheme:light; --page:#fbf7ee; --panel:#f2eadc; --panel-strong:#fffdf8; --ink:#211f1b; --body:#514d45; --muted:#777168; --line:#d9cfbf; --accent:#a85f16; --teal:#167b70; --code:#e9e2d6; }
    :root[data-theme="dark"] { color-scheme:dark; --page:#151514; --panel:#1d1d1b; --panel-strong:#101110; --ink:#f6f2e8; --body:#d3cfc5; --muted:#aaa69d; --line:#31312f; --accent:#f4be5b; --teal:#72d6c9; --code:#222321; }
    * { box-sizing:border-box; }
    html { height:100%; overflow:hidden; }
    body { height:100%; margin:0; overflow:auto; overscroll-behavior:contain; background:var(--page); color:var(--ink); font:17px/1.7 Inter,ui-sans-serif,system-ui,sans-serif; }
    article { width:min(100%,920px); margin:0 auto; padding:48px 32px 80px; }
    .eyebrow { margin:0 0 12px; color:var(--accent); font-size:12px; font-weight:800; letter-spacing:.16em; text-transform:uppercase; }
    h1 { max-width:680px; margin:0 0 22px; font:700 clamp(38px,7vw,70px)/.98 Georgia,serif; letter-spacing:-.045em; }
    h2 { margin:54px 0 12px; font:700 30px/1.1 Georgia,serif; letter-spacing:-.025em; }
    h3 { margin:36px 0 8px; font-size:18px; }
    p,li { color:var(--body); }
    strong { color:var(--ink); }
    code { color:var(--teal); background:var(--code); padding:.12em .35em; border-radius:5px; }
    pre { overflow:auto; padding:20px; border:1px solid var(--line); border-radius:14px; background:var(--panel-strong); }
    pre code { padding:0; background:none; color:var(--body); }
    .lead { color:var(--ink); font-size:21px; line-height:1.6; }
    .concept { margin:28px 0; padding:22px 24px; border-left:3px solid var(--accent); background:var(--panel); border-radius:0 14px 14px 0; }
    .concept p { margin:0; }
    .trace { display:grid; gap:10px; margin:24px 0; }
    .trace div { padding:13px 16px; border:1px solid var(--line); border-radius:10px; background:var(--panel); }
    .trace b { color:var(--teal); }
    .mermaid-diagram { margin:28px 0; padding:20px; overflow:auto; border:1px solid var(--line); border-radius:14px; background:var(--panel-strong); }
    .mermaid-diagram svg { display:block; width:100%; min-width:460px; height:auto; margin:0 auto; }
    .mermaid-error { margin:28px 0; padding:18px 20px; border:1px solid var(--accent); border-radius:14px; background:var(--panel); }
    .mermaid-error p { margin:0 0 12px; }
    .mermaid-error pre { margin:0; }
    details { margin:22px 0; border:1px solid var(--line); border-radius:12px; background:var(--panel); }
    summary { cursor:pointer; padding:15px 18px; color:var(--ink); font-weight:700; }
    details > div { padding:0 18px 16px; }
    table { width:100%; border-collapse:collapse; margin:24px 0; }
    th,td { padding:12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
    th { color:var(--accent); font-size:12px; letter-spacing:.08em; text-transform:uppercase; }
    .check { color:var(--teal); }
    @media (max-width:600px) { article { padding:34px 18px 64px; } h1 { font-size:42px; } }
  </style>
</head>
<body><article>{{CONTENT}}</article></body>
</html>"""


def create_app(
    *,
    courses_root: Path | None = None,
    progress_root: Path | None = None,
    mount_frontend: bool = True,
) -> FastAPI:
    application = FastAPI(title="Socraites API", version="0.1.0")
    course_store = CourseStore(courses_root or DATA_ROOT / "courses")
    progress_store = ProgressStore(progress_root or DATA_ROOT / "progress")
    judge_service = JudgeService(PROJECT_ROOT)
    mermaid_renderer = MermaidRenderer(PROJECT_ROOT / "agent-runtime" / "render-mermaid.mjs")

    def combined_quiz(course_id: str, lesson_id: str) -> tuple[Quiz, int]:
        authored = course_store.quiz(course_id, lesson_id)
        generated = progress_store.generated_questions(course_id, lesson_id)
        return authored.model_copy(update={"questions": [*authored.questions, *generated]}), len(authored.questions)

    @application.exception_handler(NotFoundError)
    async def not_found(_: Request, error: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": str(error)})

    @application.exception_handler(InvalidDataError)
    async def invalid_data(_: Request, error: InvalidDataError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"error": str(error)})

    @application.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/api/judge/status")
    async def judge_status() -> Any:
        return judge_service.status()

    @application.get("/api/courses")
    async def list_courses() -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for course in course_store.list_courses():
            progress = progress_store.read(course.id)
            completed = sum(1 for item in progress.lessons.values() if item.passed)
            workspace = progress_store.workspace(course.id, course.lessons[0].id)
            summaries.append({
                "id": course.id,
                "title": course.title,
                "category": course.category,
                "subtitle": course.subtitle,
                "description": course.description,
                "section_count": len(course.lessons),
                "estimated_minutes": sum(item.estimated_minutes for item in course.lessons),
                "completed_sections": completed,
                "progress": completed / len(course.lessons),
                "last_opened_at": workspace.updated_at,
            })
        return summaries

    @application.get("/api/courses/{course_id}", response_model=CourseView)
    async def get_course(course_id: str) -> CourseView:
        return CourseView(course=course_store.course(course_id), progress=progress_store.read(course_id))

    @application.get("/api/courses/{course_id}/workspace", response_model=WorkspaceView)
    async def get_workspace(course_id: str) -> WorkspaceView:
        course = course_store.course(course_id)
        return progress_store.workspace(course_id, course.lessons[0].id)

    @application.put("/api/courses/{course_id}/workspace", response_model=WorkspaceView)
    async def update_workspace(
        course_id: str,
        request: WorkspaceNavigationRequest,
    ) -> WorkspaceView:
        course = course_store.course(course_id)
        if not any(item.id == request.active_lesson_id for item in course.lessons):
            raise NotFoundError("lesson not found")
        return progress_store.update_navigation(
            course_id,
            course.lessons[0].id,
            request.active_lesson_id,
            request.active_phase,
        )

    @application.put(
        "/api/courses/{course_id}/lessons/{lesson_id}/draft",
        response_model=WorkspaceView,
    )
    async def save_draft(
        course_id: str,
        lesson_id: str,
        request: DraftRequest,
    ) -> WorkspaceView:
        course = course_store.course(course_id)
        if not any(item.id == lesson_id for item in course.lessons):
            raise NotFoundError("lesson not found")
        return progress_store.save_draft(
            course_id,
            course.lessons[0].id,
            lesson_id,
            request.answers,
        )

    @application.get(
        "/api/courses/{course_id}/lessons/{lesson_id}/quiz",
        response_model=PublicQuiz,
    )
    async def get_quiz(course_id: str, lesson_id: str) -> PublicQuiz:
        quiz, authored_count = combined_quiz(course_id, lesson_id)
        return course_store.to_public_quiz(quiz, authored_count)

    @application.get(
        "/api/courses/{course_id}/lessons/{lesson_id}/tutor",
        response_model=TutorView,
    )
    async def get_tutor(course_id: str, lesson_id: str) -> TutorView:
        course = course_store.course(course_id)
        if not any(item.id == lesson_id for item in course.lessons):
            raise NotFoundError("lesson not found")
        return progress_store.tutor_view(course_id, lesson_id)

    @application.post(
        "/api/courses/{course_id}/lessons/{lesson_id}/tutor/conversations",
        response_model=TutorView,
    )
    async def new_tutor_conversation(course_id: str, lesson_id: str) -> TutorView:
        course = course_store.course(course_id)
        if not any(item.id == lesson_id for item in course.lessons):
            raise NotFoundError("lesson not found")
        return progress_store.start_tutor_conversation(course_id, lesson_id)

    @application.post(
        "/api/courses/{course_id}/lessons/{lesson_id}/tutor/conversations/{conversation_id}/activate",
        response_model=TutorView,
    )
    async def activate_tutor_conversation(
        course_id: str,
        lesson_id: str,
        conversation_id: str,
    ) -> TutorView:
        course = course_store.course(course_id)
        if not any(item.id == lesson_id for item in course.lessons):
            raise NotFoundError("lesson not found")
        return progress_store.activate_tutor_conversation(course_id, lesson_id, conversation_id)

    @application.post(
        "/api/courses/{course_id}/lessons/{lesson_id}/tutor/messages",
        response_model=TutorView,
    )
    async def send_tutor_message(
        course_id: str,
        lesson_id: str,
        request: TutorMessageRequest,
    ) -> TutorView:
        course = course_store.course(course_id)
        lesson = next((item for item in course.lessons if item.id == lesson_id), None)
        if lesson is None:
            raise NotFoundError("lesson not found")
        user_text = request.text.strip()
        if not user_text:
            raise HTTPException(status_code=422, detail="Tutor message cannot be blank")
        view, turn = progress_store.start_tutor_turn(course_id, lesson_id, user_text)
        conversation = view.conversation
        if conversation is None:
            raise InvalidDataError("tutor conversation could not be loaded")
        _, lesson_html = course_store.lesson_html(course_id, lesson_id)
        lesson_quiz = course_store.quiz(course_id, lesson_id)
        history = [item for item in conversation.turns if item.turn_id != turn.turn_id and item.status == "completed"]
        try:
            tutor_reply = await judge_service.tutor(
                course.title,
                lesson.title,
                lesson_html,
                lesson_quiz,
                history,
                user_text,
            )
            course_store.update_lesson_assets(
                course_id,
                lesson_id,
                tutor_reply.lesson_html,
                tutor_reply.quiz_json,
            )
        except JudgeUnavailable as exc:
            progress_store.fail_tutor_turn(
                course_id,
                lesson_id,
                conversation.conversation_id,
                turn.turn_id,
                str(exc),
            )
            return JSONResponse(status_code=503, content={"error": str(exc)})  # type: ignore[return-value]
        except Exception:
            progress_store.fail_tutor_turn(
                course_id,
                lesson_id,
                conversation.conversation_id,
                turn.turn_id,
                "The tutor response was interrupted.",
            )
            raise
        return progress_store.complete_tutor_turn(
            course_id,
            lesson_id,
            conversation.conversation_id,
            turn.turn_id,
            tutor_reply.text,
        )

    @application.post(
        "/api/courses/{course_id}/lessons/{lesson_id}/questions/generate",
        response_model=PublicQuiz,
    )
    async def generate_questions(course_id: str, lesson_id: str) -> PublicQuiz:
        course = course_store.course(course_id)
        lesson = next((item for item in course.lessons if item.id == lesson_id), None)
        if lesson is None:
            raise NotFoundError("lesson not found")
        current_quiz, authored_count = combined_quiz(course_id, lesson_id)
        _, lesson_html = course_store.lesson_html(course_id, lesson_id)
        try:
            questions = await judge_service.generate_questions(
                course.title,
                lesson.title,
                lesson_html,
                current_quiz,
            )
        except JudgeUnavailable as exc:
            return JSONResponse(status_code=503, content={"error": str(exc)})  # type: ignore[return-value]
        existing_ids = {question.id for question in current_quiz.questions}
        if any(question.id in existing_ids for question in questions):
            raise InvalidDataError("generated question id already exists")
        progress_store.record_generated_questions(course_id, lesson_id, questions)
        updated = current_quiz.model_copy(update={"questions": [*current_quiz.questions, *questions]})
        return course_store.to_public_quiz(updated, authored_count)

    @application.get("/render/courses/{course_id}/lessons/{lesson_id}", response_class=HTMLResponse)
    async def render_lesson(
        course_id: str,
        lesson_id: str,
        theme: Literal["light", "dark"] = "dark",
    ) -> HTMLResponse:
        _, fragment = course_store.lesson_html(course_id, lesson_id)
        fragment = await mermaid_renderer.render_fragment(fragment)
        return HTMLResponse(
            LESSON_SHELL.replace("{{THEME}}", theme).replace("{{CONTENT}}", fragment),
            headers=LESSON_HEADERS,
        )

    @application.post(
        "/api/courses/{course_id}/lessons/{lesson_id}/attempts",
        response_model=AttemptResult,
    )
    async def submit_attempt(course_id: str, lesson_id: str, request: AttemptRequest) -> AttemptResult:
        course = course_store.course(course_id)
        if not any(item.id == lesson_id for item in course.lessons):
            raise NotFoundError("lesson not found")
        quiz, _ = combined_quiz(course_id, lesson_id)
        attempt_id = str(uuid4())
        progress_store.start_grading(
            course_id,
            course.lessons[0].id,
            lesson_id,
            attempt_id,
            request.answers,
        )
        results: list[QuestionResult] = []
        try:
            for question in quiz.questions:
                answer = request.answers.get(question.id)
                if isinstance(question, SingleChoiceQuestion):
                    selected = [answer] if isinstance(answer, str) else []
                    result = _deterministic_result(question, selected == question.correct_option_ids)
                elif isinstance(question, MultipleChoiceQuestion):
                    selected = set(answer) if isinstance(answer, list) and all(isinstance(item, str) for item in answer) else set()
                    result = _deterministic_result(question, selected == set(question.correct_option_ids))
                elif isinstance(question, OrderingQuestion):
                    selected = answer if isinstance(answer, list) and all(isinstance(item, str) for item in answer) else []
                    correct_positions = sum(
                        1 for index, option_id in enumerate(question.correct_order)
                        if index < len(selected) and selected[index] == option_id
                    )
                    score = correct_positions / len(question.correct_order)
                    result = _scored_result(question, score, "local-ordering")
                else:
                    text = answer.strip() if isinstance(answer, str) else ""
                    judged: JudgeResult = await judge_service.judge(question, text)
                    result = QuestionResult(
                        question_id=question.id,
                        score=judged.score,
                        earned_points=round(judged.score * question.points, 2),
                        possible_points=question.points,
                        verdict=judged.verdict,
                        feedback=judged.feedback,
                        explanation=question.explanation,
                        strengths=judged.strengths,
                        improvements=judged.improvements,
                        judge=judged.judge,
                    )
                results.append(result)
        except JudgeUnavailable as exc:
            progress_store.fail_grading(
                course_id,
                course.lessons[0].id,
                lesson_id,
                attempt_id,
                str(exc),
            )
            return JSONResponse(status_code=503, content={"error": str(exc)})  # type: ignore[return-value]
        except Exception:
            progress_store.fail_grading(
                course_id,
                course.lessons[0].id,
                lesson_id,
                attempt_id,
                "Grading was interrupted. Your answers are still saved.",
            )
            raise

        possible = sum(item.possible_points for item in results)
        score = sum(item.earned_points for item in results) / possible
        attempt = AttemptResult(
            attempt_id=attempt_id,
            course_id=course_id,
            lesson_id=lesson_id,
            created_at=datetime.now(UTC),
            answers=request.answers,
            score=round(score, 4),
            passed=score >= quiz.passing_score,
            results=results,
        )
        progress_store.record(attempt)
        return attempt

    if mount_frontend:
        frontend_dist = PROJECT_ROOT / "frontend" / "dist"
        if frontend_dist.is_dir():
            application.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return application


def _deterministic_result(question: Any, correct: bool) -> QuestionResult:
    return _scored_result(question, 1.0 if correct else 0.0, "local-exact")


def _scored_result(question: Any, score: float, judge: str) -> QuestionResult:
    verdict = (
        JudgeVerdict.CORRECT
        if score >= 0.999
        else JudgeVerdict.PARTIAL
        if score > 0
        else JudgeVerdict.INCORRECT
    )
    return QuestionResult(
        question_id=question.id,
        score=score,
        earned_points=round(score * question.points, 2),
        possible_points=question.points,
        verdict=verdict,
        feedback="Correct." if verdict == JudgeVerdict.CORRECT else "Review the explanation and try again.",
        explanation=question.explanation,
        strengths=[],
        improvements=[],
        judge=judge,
    )


app = create_app()
