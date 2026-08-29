from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class LessonRef(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=280)
    estimated_minutes: int = Field(ge=1, le=180)
    lesson_file: str = Field(min_length=1)
    quiz_file: str = Field(min_length=1)


class CourseManifest(StrictModel):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=80)
    subtitle: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=1, max_length=800)
    lessons: list[LessonRef] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_lessons(self) -> "CourseManifest":
        ids = [lesson.id for lesson in self.lessons]
        if len(ids) != len(set(ids)):
            raise ValueError("lesson ids must be unique")
        return self


class ChoiceOption(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    label: str = Field(min_length=1, max_length=500)


class QuestionBase(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    prompt: str = Field(min_length=1, max_length=2000)
    explanation: str = Field(min_length=1, max_length=3000)
    points: float = Field(gt=0, le=100)


class SingleChoiceQuestion(QuestionBase):
    type: Literal["single_choice"]
    options: list[ChoiceOption] = Field(min_length=2, max_length=8)
    correct_option_ids: list[str] = Field(min_length=1, max_length=1)


class MultipleChoiceQuestion(QuestionBase):
    type: Literal["multiple_choice"]
    options: list[ChoiceOption] = Field(min_length=2, max_length=10)
    correct_option_ids: list[str] = Field(min_length=1)


class OrderingQuestion(QuestionBase):
    type: Literal["ordering"]
    options: list[ChoiceOption] = Field(min_length=2, max_length=10)
    correct_order: list[str] = Field(min_length=2)


class FreeResponseQuestion(QuestionBase):
    type: Literal["free_response"]
    rubric: str = Field(min_length=1, max_length=4000)
    reference_answer: str = Field(min_length=1, max_length=4000)


Question = Annotated[
    SingleChoiceQuestion
    | MultipleChoiceQuestion
    | OrderingQuestion
    | FreeResponseQuestion,
    Field(discriminator="type"),
]


class Quiz(StrictModel):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=1, max_length=140)
    passing_score: float = Field(ge=0, le=1)
    questions: list[Question] = Field(min_length=1)


class PublicQuestion(StrictModel):
    id: str
    type: Literal["single_choice", "multiple_choice", "ordering", "free_response"]
    prompt: str
    points: float
    options: list[ChoiceOption] | None = None


class PublicQuiz(StrictModel):
    id: str
    title: str
    passing_score: float
    questions: list[PublicQuestion]
    authored_question_count: int = Field(ge=0)
    generated_question_count: int = Field(ge=0)


class GeneratedQuestionSet(StrictModel):
    schema_version: Literal[1] = 1
    generation_id: str
    course_id: str
    lesson_id: str
    created_at: datetime
    source: Literal["codex-acp"] = "codex-acp"
    questions: list[Question] = Field(min_length=1, max_length=5)


class AttemptRequest(StrictModel):
    answers: dict[str, JsonValue]


class DraftRequest(StrictModel):
    answers: dict[str, JsonValue]


class WorkspaceNavigationRequest(StrictModel):
    active_lesson_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    active_phase: Literal["lesson", "quiz"]


class JudgeVerdict(StrEnum):
    CORRECT = "correct"
    PARTIAL = "partial"
    INCORRECT = "incorrect"


class JudgeResult(StrictModel):
    score: float = Field(ge=0, le=1)
    verdict: JudgeVerdict
    feedback: str = Field(min_length=1, max_length=3000)
    strengths: list[str] = Field(default_factory=list, max_length=6)
    improvements: list[str] = Field(default_factory=list, max_length=6)
    judge: str = Field(min_length=1, max_length=80)


class QuestionResult(StrictModel):
    question_id: str
    score: float = Field(ge=0, le=1)
    earned_points: float = Field(ge=0)
    possible_points: float = Field(gt=0)
    verdict: JudgeVerdict
    feedback: str
    explanation: str
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    judge: str


class AttemptResult(StrictModel):
    attempt_id: str
    course_id: str
    lesson_id: str
    created_at: datetime
    answers: dict[str, JsonValue] = Field(default_factory=dict)
    score: float = Field(ge=0, le=1)
    passed: bool
    results: list[QuestionResult]


class LessonProgress(StrictModel):
    lesson_id: str
    attempts: int = Field(ge=0)
    best_score: float = Field(ge=0, le=1)
    passed: bool
    last_attempt_at: datetime | None = None


class CourseProgress(StrictModel):
    course_id: str
    learner_id: str
    updated_at: datetime | None = None
    lessons: dict[str, LessonProgress] = Field(default_factory=dict)


class CourseView(StrictModel):
    course: CourseManifest
    progress: CourseProgress


class QuizDraft(StrictModel):
    lesson_id: str
    answers: dict[str, JsonValue] = Field(default_factory=dict)
    status: Literal["editing", "grading", "graded"] = "editing"
    updated_at: datetime | None = None
    grading_started_at: datetime | None = None
    latest_attempt_id: str | None = None
    error: str | None = None


class LearnerWorkspace(StrictModel):
    schema_version: Literal[1] = 1
    course_id: str
    learner_id: str
    active_lesson_id: str
    active_phase: Literal["lesson", "quiz"] = "lesson"
    updated_at: datetime | None = None
    lessons: dict[str, QuizDraft] = Field(default_factory=dict)


class LessonWorkView(QuizDraft):
    latest_attempt: AttemptResult | None = None


class WorkspaceView(StrictModel):
    schema_version: Literal[1] = 1
    course_id: str
    learner_id: str
    active_lesson_id: str
    active_phase: Literal["lesson", "quiz"]
    updated_at: datetime | None = None
    lessons: dict[str, LessonWorkView] = Field(default_factory=dict)


class TutorTurn(StrictModel):
    turn_id: str
    user_text: str = Field(min_length=1, max_length=6000)
    assistant_text: str | None = Field(default=None, max_length=16000)
    status: Literal["generating", "completed", "failed"] = "generating"
    created_at: datetime
    updated_at: datetime
    error: str | None = Field(default=None, max_length=1000)


class TutorConversation(StrictModel):
    schema_version: Literal[1] = 1
    conversation_id: str
    course_id: str
    lesson_id: str
    title: str = Field(min_length=1, max_length=120)
    created_at: datetime
    updated_at: datetime
    turns: list[TutorTurn] = Field(default_factory=list)


class TutorConversationSummary(StrictModel):
    conversation_id: str
    title: str
    updated_at: datetime
    turn_count: int = Field(ge=0)


class TutorView(StrictModel):
    active_conversation_id: str | None = None
    conversation: TutorConversation | None = None
    conversations: list[TutorConversationSummary] = Field(default_factory=list)


class TutorMessageRequest(StrictModel):
    text: str = Field(min_length=1, max_length=6000)


class InteractionEvent(StrictModel):
    schema_version: Literal[1] = 1
    event_id: str
    kind: Literal[
        "navigation_changed",
        "draft_saved",
        "grading_started",
        "grading_completed",
        "grading_failed",
        "questions_generated",
        "tutor_conversation_started",
        "tutor_turn_started",
        "tutor_turn_completed",
        "tutor_turn_failed",
    ]
    created_at: datetime
    course_id: str
    lesson_id: str | None = None
    phase: Literal["lesson", "quiz"] | None = None
    attempt_id: str | None = None
    answers: dict[str, JsonValue] | None = None
    result: AttemptResult | None = None
    generation_id: str | None = None
    question_ids: list[str] | None = None
    conversation_id: str | None = None
    turn_id: str | None = None
    user_text: str | None = None
    assistant_text: str | None = None
    error: str | None = None


class JudgeStatus(StrictModel):
    configured_mode: str
    active_mode: str
    available: bool
    detail: str
