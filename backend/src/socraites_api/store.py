from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from .models import (
    AttemptResult,
    CourseManifest,
    CourseProgress,
    GeneratedQuestionSet,
    InteractionEvent,
    LearnerWorkspace,
    LessonProgress,
    LessonWorkView,
    PublicFillParagraphBlank,
    PublicQuestion,
    PublicQuiz,
    Question,
    QuizDraft,
    Quiz,
    TutorConversation,
    TutorConversationSummary,
    TutorTurn,
    TutorView,
    WorkspaceView,
)

SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class StoreError(RuntimeError):
    pass


class NotFoundError(StoreError):
    pass


class InvalidDataError(StoreError):
    pass


def _safe_id(value: str, label: str) -> str:
    if not SAFE_ID.fullmatch(value):
        raise NotFoundError(f"invalid {label}")
    return value


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise NotFoundError(f"file not found: {path.name}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidDataError(f"cannot read {path.name}") from exc


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class CourseStore:
    def __init__(self, courses_root: Path) -> None:
        self.root = courses_root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def list_courses(self) -> list[CourseManifest]:
        if not self.root.exists():
            return []
        courses: list[CourseManifest] = []
        for manifest in sorted(self.root.glob("*/course.json")):
            courses.append(self._parse_manifest(manifest))
        return courses

    def course(self, course_id: str) -> CourseManifest:
        course_id = _safe_id(course_id, "course id")
        return self._parse_manifest(self.root / course_id / "course.json")

    def lesson_html(self, course_id: str, lesson_id: str) -> tuple[CourseManifest, str]:
        manifest = self.course(course_id)
        lesson = next((item for item in manifest.lessons if item.id == lesson_id), None)
        if lesson is None:
            raise NotFoundError("lesson not found")
        path = self._bounded_path(self.root / manifest.id, lesson.lesson_file)
        try:
            return manifest, path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise NotFoundError("lesson file not found") from exc
        except OSError as exc:
            raise InvalidDataError("lesson file could not be read") from exc

    def quiz(self, course_id: str, lesson_id: str) -> Quiz:
        manifest = self.course(course_id)
        lesson = next((item for item in manifest.lessons if item.id == lesson_id), None)
        if lesson is None:
            raise NotFoundError("lesson not found")
        path = self._bounded_path(self.root / manifest.id, lesson.quiz_file)
        try:
            return Quiz.model_validate(_read_json(path))
        except ValidationError as exc:
            raise InvalidDataError("quiz file is invalid") from exc

    def update_lesson_assets(
        self,
        course_id: str,
        lesson_id: str,
        lesson_html: str,
        quiz_payload: str,
    ) -> bool:
        """Validate and atomically persist edits to one authored lesson and quiz."""
        manifest = self.course(course_id)
        lesson = next((item for item in manifest.lessons if item.id == lesson_id), None)
        if lesson is None:
            raise NotFoundError("lesson not found")

        fragment = lesson_html.strip()
        if not fragment:
            raise InvalidDataError("edited lesson cannot be empty")
        if len(fragment) > 200_000:
            raise InvalidDataError("edited lesson is too large")
        if re.search(r"<\s*(?:html|head|body|style|script|form|iframe)\b", fragment, re.IGNORECASE):
            raise InvalidDataError("edited lesson contains a forbidden HTML element")

        try:
            quiz = Quiz.model_validate_json(quiz_payload)
        except ValidationError as exc:
            raise InvalidDataError("edited quiz file is invalid") from exc
        current_quiz = self.quiz(course_id, lesson_id)
        if quiz.id != current_quiz.id:
            raise InvalidDataError("edited quiz must preserve its id")

        course_root = self.root / manifest.id
        lesson_path = self._bounded_path(course_root, lesson.lesson_file)
        quiz_path = self._bounded_path(course_root, lesson.quiz_file)
        normalized_html = fragment + "\n"
        lesson_changed = lesson_path.read_text(encoding="utf-8").strip() != fragment
        quiz_changed = current_quiz != quiz
        if not lesson_changed and not quiz_changed:
            return False

        with self._lock:
            if lesson_changed:
                _atomic_text(lesson_path, normalized_html)
            if quiz_changed:
                _atomic_json(quiz_path, quiz.model_dump(mode="json"))
        return True

    def public_quiz(self, course_id: str, lesson_id: str) -> PublicQuiz:
        return self.to_public_quiz(self.quiz(course_id, lesson_id))

    @staticmethod
    def to_public_quiz(quiz: Quiz, authored_question_count: int | None = None) -> PublicQuiz:
        authored_count = authored_question_count if authored_question_count is not None else len(quiz.questions)
        questions = []
        for question in quiz.questions:
            options = getattr(question, "options", None)
            source_blanks = getattr(question, "blanks", None)
            blanks = (
                [PublicFillParagraphBlank(id=blank.id, options=blank.options) for blank in source_blanks]
                if source_blanks is not None
                else None
            )
            questions.append(
                PublicQuestion(
                    id=question.id,
                    type=question.type,
                    prompt=question.prompt,
                    points=question.points,
                    options=options,
                    blanks=blanks,
                )
            )
        return PublicQuiz(
            id=quiz.id,
            title=quiz.title,
            passing_score=quiz.passing_score,
            questions=questions,
            authored_question_count=authored_count,
            generated_question_count=len(quiz.questions) - authored_count,
        )

    def _parse_manifest(self, path: Path) -> CourseManifest:
        try:
            manifest = CourseManifest.model_validate(_read_json(path))
        except ValidationError as exc:
            raise InvalidDataError(f"invalid course manifest: {path}") from exc
        if manifest.id != path.parent.name:
            raise InvalidDataError("course id must match its directory")
        return manifest

    @staticmethod
    def _bounded_path(root: Path, relative: str) -> Path:
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root.resolve()):
            raise InvalidDataError("course path escapes its directory")
        return candidate


class ProgressStore:
    def __init__(self, root: Path, learner_id: str = "local") -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.learner_id = _safe_id(learner_id, "learner id")
        self._lock = RLock()

    def read(self, course_id: str) -> CourseProgress:
        course_id = _safe_id(course_id, "course id")
        path = self._course_root(course_id) / "progress.json"
        if not path.exists():
            return CourseProgress(course_id=course_id, learner_id=self.learner_id)
        try:
            return CourseProgress.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            raise InvalidDataError("progress file is invalid") from exc

    def generated_questions(self, course_id: str, lesson_id: str) -> list[Question]:
        course_id = _safe_id(course_id, "course id")
        lesson_id = _safe_id(lesson_id, "lesson id")
        questions: list[Question] = []
        generated_root = self._course_root(course_id) / "generated" / lesson_id
        for path in sorted(generated_root.glob("*.json")):
            try:
                generated = GeneratedQuestionSet.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValidationError) as exc:
                raise InvalidDataError("generated question file is invalid") from exc
            questions.extend(generated.questions)
        return questions

    def record_generated_questions(
        self,
        course_id: str,
        lesson_id: str,
        questions: list[Question],
    ) -> GeneratedQuestionSet:
        course_id = _safe_id(course_id, "course id")
        lesson_id = _safe_id(lesson_id, "lesson id")
        with self._lock:
            generation = GeneratedQuestionSet(
                generation_id=str(uuid4()),
                course_id=course_id,
                lesson_id=lesson_id,
                created_at=datetime.now(UTC),
                questions=questions,
            )
            timestamp = generation.created_at.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            path = (
                self._course_root(course_id)
                / "generated"
                / lesson_id
                / f"{timestamp}_{generation.generation_id}.json"
            )
            _atomic_json(path, generation.model_dump(mode="json"))
            self._write_event(
                InteractionEvent(
                    event_id=str(uuid4()),
                    kind="questions_generated",
                    created_at=generation.created_at,
                    course_id=course_id,
                    lesson_id=lesson_id,
                    phase="quiz",
                    generation_id=generation.generation_id,
                    question_ids=[question.id for question in questions],
                )
            )
            return generation

    def tutor_view(self, course_id: str, lesson_id: str) -> TutorView:
        course_id = _safe_id(course_id, "course id")
        lesson_id = _safe_id(lesson_id, "lesson id")
        with self._lock:
            root = self._tutor_root(course_id, lesson_id)
            conversations: list[TutorConversation] = []
            for path in root.glob("*.json"):
                if path.name == "state.json":
                    continue
                try:
                    conversations.append(TutorConversation.model_validate_json(path.read_text(encoding="utf-8")))
                except (OSError, ValidationError) as exc:
                    raise InvalidDataError("tutor conversation file is invalid") from exc
            conversations.sort(key=lambda item: item.updated_at, reverse=True)
            active_id: str | None = None
            state_path = root / "state.json"
            if state_path.exists():
                state = _read_json(state_path)
                if not isinstance(state, dict) or not isinstance(state.get("active_conversation_id"), str):
                    raise InvalidDataError("tutor state file is invalid")
                active_id = state["active_conversation_id"]
            elif conversations:
                active_id = conversations[0].conversation_id
            current = next((item for item in conversations if item.conversation_id == active_id), None)
            if active_id and current is None:
                raise InvalidDataError("tutor state references a missing conversation")
            return TutorView(
                active_conversation_id=active_id,
                conversation=current,
                conversations=[
                    TutorConversationSummary(
                        conversation_id=item.conversation_id,
                        title=item.title,
                        updated_at=item.updated_at,
                        turn_count=len(item.turns),
                    )
                    for item in conversations
                ],
            )

    def start_tutor_conversation(self, course_id: str, lesson_id: str) -> TutorView:
        course_id = _safe_id(course_id, "course id")
        lesson_id = _safe_id(lesson_id, "lesson id")
        with self._lock:
            now = datetime.now(UTC)
            conversation = TutorConversation(
                conversation_id=str(uuid4()),
                course_id=course_id,
                lesson_id=lesson_id,
                title="New conversation",
                created_at=now,
                updated_at=now,
            )
            self._write_tutor_conversation(conversation)
            _atomic_json(
                self._tutor_root(course_id, lesson_id) / "state.json",
                {"active_conversation_id": conversation.conversation_id},
            )
            self._write_event(
                InteractionEvent(
                    event_id=str(uuid4()),
                    kind="tutor_conversation_started",
                    created_at=now,
                    course_id=course_id,
                    lesson_id=lesson_id,
                    phase="lesson",
                    conversation_id=conversation.conversation_id,
                )
            )
            return self.tutor_view(course_id, lesson_id)

    def activate_tutor_conversation(
        self,
        course_id: str,
        lesson_id: str,
        conversation_id: str,
    ) -> TutorView:
        course_id = _safe_id(course_id, "course id")
        lesson_id = _safe_id(lesson_id, "lesson id")
        conversation_id = _safe_id(conversation_id, "conversation id")
        with self._lock:
            self._read_tutor_conversation(course_id, lesson_id, conversation_id)
            _atomic_json(
                self._tutor_root(course_id, lesson_id) / "state.json",
                {"active_conversation_id": conversation_id},
            )
            return self.tutor_view(course_id, lesson_id)

    def start_tutor_turn(
        self,
        course_id: str,
        lesson_id: str,
        user_text: str,
    ) -> tuple[TutorView, TutorTurn]:
        with self._lock:
            view = self.tutor_view(course_id, lesson_id)
            if view.conversation is None:
                view = self.start_tutor_conversation(course_id, lesson_id)
            conversation = view.conversation
            if conversation is None:
                raise InvalidDataError("tutor conversation could not be created")
            if any(turn.status == "generating" for turn in conversation.turns):
                raise InvalidDataError("the tutor is already answering")
            now = datetime.now(UTC)
            turn = TutorTurn(
                turn_id=str(uuid4()),
                user_text=user_text,
                created_at=now,
                updated_at=now,
            )
            updated = conversation.model_copy(
                update={
                    "title": (user_text.strip().replace("\n", " ")[:80] or "New conversation") if not conversation.turns else conversation.title,
                    "updated_at": now,
                    "turns": [*conversation.turns, turn],
                }
            )
            self._write_tutor_conversation(updated)
            self._write_event(
                InteractionEvent(
                    event_id=str(uuid4()),
                    kind="tutor_turn_started",
                    created_at=now,
                    course_id=course_id,
                    lesson_id=lesson_id,
                    phase="lesson",
                    conversation_id=conversation.conversation_id,
                    turn_id=turn.turn_id,
                    user_text=user_text,
                )
            )
            return self.tutor_view(course_id, lesson_id), turn

    def complete_tutor_turn(
        self,
        course_id: str,
        lesson_id: str,
        conversation_id: str,
        turn_id: str,
        assistant_text: str,
    ) -> TutorView:
        return self._finish_tutor_turn(
            course_id,
            lesson_id,
            conversation_id,
            turn_id,
            assistant_text=assistant_text,
        )

    def fail_tutor_turn(
        self,
        course_id: str,
        lesson_id: str,
        conversation_id: str,
        turn_id: str,
        error: str,
    ) -> TutorView:
        return self._finish_tutor_turn(
            course_id,
            lesson_id,
            conversation_id,
            turn_id,
            error=error,
        )

    def _finish_tutor_turn(
        self,
        course_id: str,
        lesson_id: str,
        conversation_id: str,
        turn_id: str,
        *,
        assistant_text: str | None = None,
        error: str | None = None,
    ) -> TutorView:
        with self._lock:
            conversation = self._read_tutor_conversation(course_id, lesson_id, conversation_id)
            now = datetime.now(UTC)
            found = False
            turns: list[TutorTurn] = []
            for turn in conversation.turns:
                if turn.turn_id != turn_id:
                    turns.append(turn)
                    continue
                found = True
                turns.append(
                    turn.model_copy(
                        update={
                            "assistant_text": assistant_text,
                            "status": "completed" if assistant_text is not None else "failed",
                            "updated_at": now,
                            "error": error,
                        }
                    )
                )
            if not found:
                raise InvalidDataError("tutor turn not found")
            self._write_tutor_conversation(
                conversation.model_copy(update={"updated_at": now, "turns": turns})
            )
            self._write_event(
                InteractionEvent(
                    event_id=str(uuid4()),
                    kind="tutor_turn_completed" if assistant_text is not None else "tutor_turn_failed",
                    created_at=now,
                    course_id=course_id,
                    lesson_id=lesson_id,
                    phase="lesson",
                    conversation_id=conversation_id,
                    turn_id=turn_id,
                    assistant_text=assistant_text,
                    error=error,
                )
            )
            return self.tutor_view(course_id, lesson_id)

    def _tutor_root(self, course_id: str, lesson_id: str) -> Path:
        return self._course_root(course_id) / "tutor" / _safe_id(lesson_id, "lesson id")

    def _write_tutor_conversation(self, conversation: TutorConversation) -> None:
        path = self._tutor_root(conversation.course_id, conversation.lesson_id) / f"{conversation.conversation_id}.json"
        _atomic_json(path, conversation.model_dump(mode="json"))

    def _read_tutor_conversation(
        self,
        course_id: str,
        lesson_id: str,
        conversation_id: str,
    ) -> TutorConversation:
        path = self._tutor_root(course_id, lesson_id) / f"{_safe_id(conversation_id, 'conversation id')}.json"
        try:
            return TutorConversation.model_validate_json(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise NotFoundError("tutor conversation not found") from exc
        except (OSError, ValidationError) as exc:
            raise InvalidDataError("tutor conversation file is invalid") from exc

    def record(self, attempt: AttemptResult) -> CourseProgress:
        with self._lock:
            course_root = self._course_root(attempt.course_id)
            attempt_path = course_root / "attempts" / f"{attempt.attempt_id}.json"
            if attempt_path.exists():
                raise InvalidDataError("attempt id already exists")
            _atomic_json(attempt_path, attempt.model_dump(mode="json"))

            progress = self.read(attempt.course_id)
            previous = progress.lessons.get(attempt.lesson_id)
            lesson_progress = LessonProgress(
                lesson_id=attempt.lesson_id,
                attempts=(previous.attempts if previous else 0) + 1,
                best_score=max(previous.best_score if previous else 0, attempt.score),
                passed=(previous.passed if previous else False) or attempt.passed,
                last_attempt_at=attempt.created_at,
            )
            lessons = dict(progress.lessons)
            lessons[attempt.lesson_id] = lesson_progress
            updated = CourseProgress(
                course_id=attempt.course_id,
                learner_id=self.learner_id,
                updated_at=datetime.now(UTC),
                lessons=lessons,
            )
            _atomic_json(course_root / "progress.json", updated.model_dump(mode="json"))
            workspace = self._read_workspace(attempt.course_id, attempt.lesson_id)
            draft = QuizDraft(
                lesson_id=attempt.lesson_id,
                answers=attempt.answers,
                status="graded",
                updated_at=datetime.now(UTC),
                latest_attempt_id=attempt.attempt_id,
            )
            lessons = dict(workspace.lessons)
            lessons[attempt.lesson_id] = draft
            self._write_workspace(
                LearnerWorkspace(
                    course_id=workspace.course_id,
                    learner_id=workspace.learner_id,
                    active_lesson_id=attempt.lesson_id,
                    active_phase="quiz",
                    updated_at=draft.updated_at,
                    lessons=lessons,
                )
            )
            self._write_event(
                InteractionEvent(
                    event_id=str(uuid4()),
                    kind="grading_completed",
                    created_at=datetime.now(UTC),
                    course_id=attempt.course_id,
                    lesson_id=attempt.lesson_id,
                    phase="quiz",
                    attempt_id=attempt.attempt_id,
                    answers=attempt.answers,
                    result=attempt,
                )
            )
            return updated

    def workspace(self, course_id: str, default_lesson_id: str) -> WorkspaceView:
        with self._lock:
            workspace = self._read_workspace(course_id, default_lesson_id)
            lessons: dict[str, LessonWorkView] = {}
            for lesson_id, draft in workspace.lessons.items():
                latest_attempt = (
                    self._read_attempt(course_id, draft.latest_attempt_id)
                    if draft.latest_attempt_id
                    else None
                )
                lessons[lesson_id] = LessonWorkView(
                    **draft.model_dump(),
                    latest_attempt=latest_attempt,
                )
            return WorkspaceView(
                schema_version=workspace.schema_version,
                course_id=workspace.course_id,
                learner_id=workspace.learner_id,
                active_lesson_id=workspace.active_lesson_id,
                active_phase=workspace.active_phase,
                updated_at=workspace.updated_at,
                lessons=lessons,
            )

    def update_navigation(
        self,
        course_id: str,
        default_lesson_id: str,
        active_lesson_id: str,
        active_phase: str,
    ) -> WorkspaceView:
        with self._lock:
            workspace = self._read_workspace(course_id, default_lesson_id)
            updated = workspace.model_copy(
                update={
                    "active_lesson_id": active_lesson_id,
                    "active_phase": active_phase,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._write_workspace(updated)
            self._write_event(
                InteractionEvent(
                    event_id=str(uuid4()),
                    kind="navigation_changed",
                    created_at=datetime.now(UTC),
                    course_id=course_id,
                    lesson_id=active_lesson_id,
                    phase=active_phase,
                )
            )
            return self.workspace(course_id, default_lesson_id)

    def save_draft(
        self,
        course_id: str,
        default_lesson_id: str,
        lesson_id: str,
        answers: dict[str, Any],
    ) -> WorkspaceView:
        with self._lock:
            workspace = self._read_workspace(course_id, default_lesson_id)
            previous = workspace.lessons.get(lesson_id)
            now = datetime.now(UTC)
            draft = QuizDraft(
                lesson_id=lesson_id,
                answers=answers,
                status="editing",
                updated_at=now,
                latest_attempt_id=previous.latest_attempt_id if previous else None,
            )
            lessons = dict(workspace.lessons)
            lessons[lesson_id] = draft
            updated = workspace.model_copy(
                update={
                    "active_lesson_id": lesson_id,
                    "active_phase": "quiz",
                    "updated_at": now,
                    "lessons": lessons,
                }
            )
            self._write_workspace(updated)
            self._write_event(
                InteractionEvent(
                    event_id=str(uuid4()),
                    kind="draft_saved",
                    created_at=now,
                    course_id=course_id,
                    lesson_id=lesson_id,
                    phase="quiz",
                    answers=answers,
                )
            )
            return self.workspace(course_id, default_lesson_id)

    def start_grading(
        self,
        course_id: str,
        default_lesson_id: str,
        lesson_id: str,
        attempt_id: str,
        answers: dict[str, Any],
    ) -> None:
        with self._lock:
            workspace = self._read_workspace(course_id, default_lesson_id)
            previous = workspace.lessons.get(lesson_id)
            if previous and previous.status == "grading":
                raise InvalidDataError("this quiz is already being graded")
            now = datetime.now(UTC)
            lessons = dict(workspace.lessons)
            lessons[lesson_id] = QuizDraft(
                lesson_id=lesson_id,
                answers=answers,
                status="grading",
                updated_at=now,
                grading_started_at=now,
                latest_attempt_id=previous.latest_attempt_id if previous else None,
            )
            self._write_workspace(
                workspace.model_copy(
                    update={
                        "active_lesson_id": lesson_id,
                        "active_phase": "quiz",
                        "updated_at": now,
                        "lessons": lessons,
                    }
                )
            )
            self._write_event(
                InteractionEvent(
                    event_id=str(uuid4()),
                    kind="grading_started",
                    created_at=now,
                    course_id=course_id,
                    lesson_id=lesson_id,
                    phase="quiz",
                    attempt_id=attempt_id,
                    answers=answers,
                )
            )

    def fail_grading(
        self,
        course_id: str,
        default_lesson_id: str,
        lesson_id: str,
        attempt_id: str,
        error: str,
    ) -> None:
        with self._lock:
            workspace = self._read_workspace(course_id, default_lesson_id)
            previous = workspace.lessons.get(lesson_id) or QuizDraft(lesson_id=lesson_id)
            now = datetime.now(UTC)
            lessons = dict(workspace.lessons)
            lessons[lesson_id] = previous.model_copy(
                update={
                    "status": "editing",
                    "updated_at": now,
                    "grading_started_at": None,
                    "error": error,
                }
            )
            self._write_workspace(
                workspace.model_copy(update={"updated_at": now, "lessons": lessons})
            )
            self._write_event(
                InteractionEvent(
                    event_id=str(uuid4()),
                    kind="grading_failed",
                    created_at=now,
                    course_id=course_id,
                    lesson_id=lesson_id,
                    phase="quiz",
                    attempt_id=attempt_id,
                    answers=previous.answers,
                    error=error,
                )
            )

    def _read_workspace(self, course_id: str, default_lesson_id: str) -> LearnerWorkspace:
        course_id = _safe_id(course_id, "course id")
        default_lesson_id = _safe_id(default_lesson_id, "lesson id")
        path = self._course_root(course_id) / "workspace.json"
        if not path.exists():
            attempts: list[AttemptResult] = []
            for attempt_path in (self._course_root(course_id) / "attempts").glob("*.json"):
                try:
                    attempts.append(AttemptResult.model_validate_json(attempt_path.read_text(encoding="utf-8")))
                except (OSError, ValidationError) as exc:
                    raise InvalidDataError("attempt file is invalid") from exc
            if attempts:
                latest_by_lesson: dict[str, AttemptResult] = {}
                for attempt in sorted(attempts, key=lambda item: item.created_at):
                    latest_by_lesson[attempt.lesson_id] = attempt
                latest = max(attempts, key=lambda item: item.created_at)
                return LearnerWorkspace(
                    course_id=course_id,
                    learner_id=self.learner_id,
                    active_lesson_id=latest.lesson_id,
                    active_phase="quiz",
                    updated_at=latest.created_at,
                    lessons={
                        lesson_id: QuizDraft(
                            lesson_id=lesson_id,
                            answers=attempt.answers,
                            status="graded",
                            updated_at=attempt.created_at,
                            latest_attempt_id=attempt.attempt_id,
                        )
                        for lesson_id, attempt in latest_by_lesson.items()
                    },
                )
            return LearnerWorkspace(course_id=course_id, learner_id=self.learner_id, active_lesson_id=default_lesson_id)
        try:
            return LearnerWorkspace.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            raise InvalidDataError("workspace file is invalid") from exc

    def _write_workspace(self, workspace: LearnerWorkspace) -> None:
        _atomic_json(
            self._course_root(workspace.course_id) / "workspace.json",
            workspace.model_dump(mode="json"),
        )

    def _read_attempt(self, course_id: str, attempt_id: str) -> AttemptResult:
        path = self._course_root(course_id) / "attempts" / f"{attempt_id}.json"
        try:
            return AttemptResult.model_validate_json(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise InvalidDataError("workspace references a missing attempt") from exc
        except (OSError, ValidationError) as exc:
            raise InvalidDataError("attempt file is invalid") from exc

    def _write_event(self, event: InteractionEvent) -> None:
        timestamp = event.created_at.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        path = (
            self._course_root(event.course_id)
            / "interactions"
            / f"{timestamp}_{event.event_id}.json"
        )
        _atomic_json(path, event.model_dump(mode="json"))

    def _course_root(self, course_id: str) -> Path:
        return self.root / self.learner_id / _safe_id(course_id, "course id")
