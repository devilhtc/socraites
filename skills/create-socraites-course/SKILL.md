---
name: create-socraites-course
description: Create or revise Socraites course manifests, indexed concepts, bite-sized HTML lessons, and JSON quizzes with 5 to 7 questions under data/courses. Use when an agent is asked to add learning content to a Socraites installation; do not use for changing the player UI or learner progress files.
---

# Create a Socraites course

Create durable course content under `data/courses/<course-id>/`. Before writing any course files, read [references/course-format.md](references/course-format.md) for the accepted schema and [references/lesson-pedagogy.md](references/lesson-pedagogy.md) for the teaching sequence.

## Workflow

1. Inspect `data/courses/` for existing IDs and overlapping courses. Create the directory if it is absent.
2. Choose a stable course ID shaped as a readable slug plus six random lowercase hexadecimal characters, such as `linear-algebra-7ac91e`. Never derive links or progress identity from the display title.
3. Plan a short sequence of lessons that reads as one continuous explanation. Each lesson should teach one coherent idea, inherit a useful question from the lesson before it, and take roughly 5 to 15 minutes.
4. Apply the `unslop` skill before drafting when it is available. Whether or not that skill is installed, follow the [prose and voice checklist](references/course-format.md#prose-and-voice) for every learner-facing string in the manifest, lessons, and quizzes.
5. Create `course.json`, including a concise course-level concept index, one HTML fragment per lesson under `lessons/`, and one matching quiz under `quizzes/`. Start from [assets/course-template](assets/course-template) when useful, but replace all example IDs and content.
6. Link important terms in lesson prose to their concept IDs using the exact marker in the format reference. Define a concept once at course level, reuse its ID across lessons, and keep the hover-card definition short enough to scan without losing the sentence underneath it.
7. Open each lesson with the scenario-to-principle sequence in the pedagogy reference. Later lessons must bridge from the previous lesson without dumping a recap. Give every substantive learning point at least one concrete example and state how the example instantiates the principle. Put extended examples in the exact collapsible form documented in the format reference. Add Mermaid diagrams, highlighted code, or a relevant YouTube video only when the medium improves the explanation.
8. Write 5 to 7 varied questions per lesson. Include explanations for every question and specific rubrics plus reference answers for free responses.
9. Validate the finished course:

   ```bash
   python3 skills/create-socraites-course/scripts/validate_course.py data/courses/<course-id>
   ```

10. Fix every reported error, then start Socraites and inspect the course as a learner. Hover and keyboard-focus each concept link to check its card in context. Read the prose aloud or at normal reading speed and remove any sentence that could fit unchanged in an unrelated course. Do not edit `data/progress/` while authoring.

## Boundaries

- Lesson files are trusted HTML fragments rendered inside Socraites' shared shell. Do not include document wrappers, scripts, stylesheets, forms, or author-written iframes. Use only the exact Mermaid, highlighted-code, and YouTube marker formats in the reference. Socraites transforms them before rendering.
- Concept IDs are stable course-level keys. Preserve them when revising definitions or display names. Do not create duplicate concepts for spelling variants; link the visible variant to the existing ID.
- Keep answer keys, rubrics, and reference answers only in quiz JSON. Never place them in learner-visible lesson metadata or frontend code.
- Preserve existing course IDs and lesson IDs when revising content so learner progress remains connected.
- Treat source accuracy separately from formatting. Research or cite authoritative material when the subject requires it; never invent facts or references.
