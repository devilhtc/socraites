import re
from pathlib import Path

from socraites_api.store import CourseStore, ProgressStore


FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "courses"


def test_course_and_public_quiz_load() -> None:
    store = CourseStore(FIXTURES_ROOT)

    course = store.course("test-course-a1b2c3")
    quiz = store.public_quiz("test-course-a1b2c3", "boundary")

    assert course.title == "Test Course"
    assert len(course.lessons) == 1
    assert quiz.questions[0].type == "single_choice"
    assert not hasattr(quiz.questions[0], "correct_option_ids")

    courses = store.list_courses()
    assert {item.title for item in courses} == {"Test Course"}
    assert len({item.id for item in courses}) == len(courses)
    assert all(re.fullmatch(r"[a-z][a-z0-9-]*-[a-f0-9]{6}", item.id) for item in courses)


def test_lessons_are_bite_sized_fragments() -> None:
    store = CourseStore(FIXTURES_ROOT)
    for course in store.list_courses():
        for lesson in course.lessons:
            _, fragment = store.lesson_html(course.id, lesson.id)
            quiz = store.public_quiz(course.id, lesson.id)
            assert "<html" not in fragment.lower()
            assert "<style" not in fragment.lower()
            assert len(fragment.split()) < 500
            assert 5 <= len(quiz.questions) <= 7
            assert fragment.count("<details><summary>") >= 3


def test_store_roots_are_created_when_missing(tmp_path: Path) -> None:
    courses_root = tmp_path / "data" / "courses"
    progress_root = tmp_path / "data" / "progress"
    store = CourseStore(courses_root)
    ProgressStore(progress_root)

    assert courses_root.is_dir()
    assert progress_root.is_dir()
    assert store.list_courses() == []
