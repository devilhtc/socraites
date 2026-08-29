#!/usr/bin/env python3
"""Validate one Socraites course directory using only the Python standard library."""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


COURSE_ID = re.compile(r"^[a-z][a-z0-9-]*-[a-f0-9]{6}$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
FORBIDDEN_TAGS = {"html", "head", "body", "style", "script", "form", "iframe"}
QUESTION_TYPES = {"single_choice", "multiple_choice", "ordering", "free_response"}
SLOP_PUNCTUATION = {
    "—": "em dash",
    "–": "en dash",
    "“": "curly double quote",
    "”": "curly double quote",
    "‘": "curly single quote",
    "’": "curly single quote",
}


class LessonParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forbidden: set[str] = set()
        self.h2_count = 0
        self.summary_text: list[str] = []
        self._in_summary = False
        self._summary_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in FORBIDDEN_TAGS:
            self.forbidden.add(tag)
        if tag == "h2":
            self.h2_count += 1
        if tag == "summary":
            self._in_summary = True
            self._summary_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "summary" and self._in_summary:
            self.summary_text.append("".join(self._summary_parts).strip())
            self._in_summary = False

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        if self._in_summary:
            self._summary_parts.append(data)


def read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing {path}")
        return None
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot parse {path}: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{path} must contain a JSON object")
        return None
    return value


def require_keys(value: dict[str, Any], expected: set[str], label: str, errors: list[str]) -> None:
    missing = expected - value.keys()
    extra = value.keys() - expected
    if missing:
        errors.append(f"{label} is missing: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"{label} has unsupported fields: {', '.join(sorted(extra))}")


def bounded_file(root: Path, relative: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(relative, str) or not relative:
        errors.append(f"{label} must be a non-empty relative path")
        return None
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        errors.append(f"{label} escapes the course directory")
        return None
    if not candidate.is_file():
        errors.append(f"{label} does not exist: {relative}")
        return None
    return candidate


def validate_lesson(path: Path, errors: list[str]) -> None:
    html = path.read_text(encoding="utf-8")
    parser = LessonParser()
    try:
        parser.feed(html)
    except Exception as exc:
        errors.append(f"{path} is not parseable HTML: {exc}")
        return
    if parser.forbidden:
        errors.append(f"{path} contains forbidden tags: {', '.join(sorted(parser.forbidden))}")
    word_count = len(re.findall(r"\b[\w'-]+\b", " ".join(parser.text_parts)))
    if word_count >= 500:
        errors.append(f"{path} has {word_count} words; lessons must stay below 500")
    details_count = html.count("<details")
    if details_count != html.count("<details><summary>"):
        errors.append(f"{path} must keep every <details><summary> opening on one line")
    if details_count != html.count("</div></details>"):
        errors.append(f"{path} must close example content as </div></details> on one line")
    examples = [text for text in parser.summary_text if text.startswith("Example:")]
    if len(examples) < 3:
        errors.append(f"{path} needs at least 3 example details blocks; found {len(examples)}")
    if len(examples) < parser.h2_count:
        errors.append(f"{path} has fewer examples ({len(examples)}) than learning sections ({parser.h2_count})")
    if re.search(r"<strong>[^<]+:</strong>", html):
        errors.append(f"{path} uses a bold label ending in a colon; write the lead-in as a sentence")


def validate_unslop_punctuation(root: Path, errors: list[str]) -> None:
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".html", ".json"} or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        found = sorted({label for mark, label in SLOP_PUNCTUATION.items() if mark in text})
        if found:
            errors.append(f"{path} contains unslopped punctuation: {', '.join(found)}")


def option_ids(question: dict[str, Any], label: str, errors: list[str]) -> list[str]:
    options = question.get("options")
    if not isinstance(options, list):
        errors.append(f"{label}.options must be an array")
        return []
    ids: list[str] = []
    for index, option in enumerate(options):
        if not isinstance(option, dict) or set(option) != {"id", "label"}:
            errors.append(f"{label}.options[{index}] must contain only id and label")
            continue
        option_id = option.get("id")
        if not isinstance(option_id, str) or not SLUG.fullmatch(option_id):
            errors.append(f"{label}.options[{index}].id is invalid")
        else:
            ids.append(option_id)
        if not isinstance(option.get("label"), str) or not option["label"].strip():
            errors.append(f"{label}.options[{index}].label is required")
    if len(ids) != len(set(ids)):
        errors.append(f"{label} has duplicate option IDs")
    return ids


def validate_question(question: Any, index: int, errors: list[str]) -> str | None:
    label = f"questions[{index}]"
    if not isinstance(question, dict):
        errors.append(f"{label} must be an object")
        return None
    kind = question.get("type")
    common = {"id", "type", "prompt", "points", "explanation"}
    specific = {
        "single_choice": {"options", "correct_option_ids"},
        "multiple_choice": {"options", "correct_option_ids"},
        "ordering": {"options", "correct_order"},
        "free_response": {"rubric", "reference_answer"},
    }
    if not isinstance(kind, str) or kind not in QUESTION_TYPES:
        errors.append(f"{label}.type must be one of {', '.join(sorted(QUESTION_TYPES))}")
        return None
    require_keys(question, common | specific[kind], label, errors)
    question_id = question.get("id")
    if not isinstance(question_id, str) or not SLUG.fullmatch(question_id):
        errors.append(f"{label}.id is invalid")
        question_id = None
    for field in ("prompt", "explanation"):
        if not isinstance(question.get(field), str) or not question[field].strip():
            errors.append(f"{label}.{field} is required")
    points = question.get("points")
    if not isinstance(points, (int, float)) or isinstance(points, bool) or not 0 < points <= 100:
        errors.append(f"{label}.points must be greater than 0 and at most 100")
    if kind == "free_response":
        for field in ("rubric", "reference_answer"):
            if not isinstance(question.get(field), str) or not question[field].strip():
                errors.append(f"{label}.{field} is required")
        return question_id
    ids = option_ids(question, label, errors)
    minimum, maximum = (2, 8) if kind == "single_choice" else (2, 10)
    if not minimum <= len(ids) <= maximum:
        errors.append(f"{label} must have {minimum}–{maximum} options")
    answer_field = "correct_order" if kind == "ordering" else "correct_option_ids"
    answers = question.get(answer_field)
    if not isinstance(answers, list) or not all(isinstance(value, str) for value in answers):
        errors.append(f"{label}.{answer_field} must be an array of option IDs")
    else:
        if len(answers) != len(set(answers)):
            errors.append(f"{label}.{answer_field} contains duplicates")
        if not set(answers) <= set(ids):
            errors.append(f"{label}.{answer_field} references unknown option IDs")
        if kind == "single_choice" and len(answers) != 1:
            errors.append(f"{label}.correct_option_ids must contain exactly one ID")
        if kind == "ordering" and set(answers) != set(ids):
            errors.append(f"{label}.correct_order must contain every option ID exactly once")
    return question_id


def validate_quiz(path: Path, errors: list[str]) -> None:
    quiz = read_json(path, errors)
    if quiz is None:
        return
    require_keys(quiz, {"schema_version", "id", "title", "passing_score", "questions"}, str(path), errors)
    if quiz.get("schema_version") != 1:
        errors.append(f"{path}.schema_version must be 1")
    if not isinstance(quiz.get("id"), str) or not SLUG.fullmatch(quiz["id"]):
        errors.append(f"{path}.id is invalid")
    if not isinstance(quiz.get("title"), str) or not quiz["title"].strip():
        errors.append(f"{path}.title is required")
    score = quiz.get("passing_score")
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 1:
        errors.append(f"{path}.passing_score must be between 0 and 1")
    questions = quiz.get("questions")
    if not isinstance(questions, list):
        errors.append(f"{path}.questions must be an array")
        return
    if not 5 <= len(questions) <= 7:
        errors.append(f"{path} must contain 5–7 questions; found {len(questions)}")
    ids = [validate_question(question, index, errors) for index, question in enumerate(questions)]
    valid_ids = [value for value in ids if value]
    if len(valid_ids) != len(set(valid_ids)):
        errors.append(f"{path} has duplicate question IDs")


def validate_course(root: Path) -> list[str]:
    errors: list[str] = []
    root = root.resolve()
    validate_unslop_punctuation(root, errors)
    manifest = read_json(root / "course.json", errors)
    if manifest is None:
        return errors
    require_keys(manifest, {"schema_version", "id", "title", "category", "subtitle", "description", "lessons"}, "course.json", errors)
    if manifest.get("schema_version") != 1:
        errors.append("course.json.schema_version must be 1")
    course_id = manifest.get("id")
    if not isinstance(course_id, str) or not COURSE_ID.fullmatch(course_id):
        errors.append("course.json.id must be a slug plus a six-character lowercase hex suffix")
    elif course_id != root.name:
        errors.append("course.json.id must match the course directory name")
    for field in ("title", "category", "subtitle", "description"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            errors.append(f"course.json.{field} is required")
    lessons = manifest.get("lessons")
    if not isinstance(lessons, list) or not lessons:
        errors.append("course.json.lessons must be a non-empty array")
        return errors
    lesson_ids: list[str] = []
    for index, lesson in enumerate(lessons):
        label = f"course.json.lessons[{index}]"
        if not isinstance(lesson, dict):
            errors.append(f"{label} must be an object")
            continue
        require_keys(lesson, {"id", "title", "summary", "estimated_minutes", "lesson_file", "quiz_file"}, label, errors)
        lesson_id = lesson.get("id")
        if not isinstance(lesson_id, str) or not SLUG.fullmatch(lesson_id):
            errors.append(f"{label}.id is invalid")
        else:
            lesson_ids.append(lesson_id)
        for field in ("title", "summary"):
            if not isinstance(lesson.get(field), str) or not lesson[field].strip():
                errors.append(f"{label}.{field} is required")
        minutes = lesson.get("estimated_minutes")
        if not isinstance(minutes, int) or isinstance(minutes, bool) or not 1 <= minutes <= 180:
            errors.append(f"{label}.estimated_minutes must be an integer from 1 to 180")
        lesson_path = bounded_file(root, lesson.get("lesson_file"), f"{label}.lesson_file", errors)
        quiz_path = bounded_file(root, lesson.get("quiz_file"), f"{label}.quiz_file", errors)
        if lesson_path:
            validate_lesson(lesson_path, errors)
        if quiz_path:
            validate_quiz(quiz_path, errors)
    if len(lesson_ids) != len(set(lesson_ids)):
        errors.append("course.json has duplicate lesson IDs")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_course.py data/courses/<course-id>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    errors = validate_course(root)
    if errors:
        print(f"Course validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Course is valid: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
