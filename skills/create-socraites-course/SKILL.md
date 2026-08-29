---
name: create-socraites-course
description: Create or revise Socraites course manifests, bite-sized HTML lessons, and 5–7 question JSON quizzes under data/courses. Use when an agent is asked to add learning content to a Socraites installation; do not use for changing the player UI or learner progress files.
---

# Create Socraites Course

Create durable course content under `data/courses/<course-id>/`. Read [references/course-format.md](references/course-format.md) before writing any course files. It defines the accepted schema, lesson markup, quiz types, and learning-quality requirements.

## Workflow

1. Inspect `data/courses/` for existing IDs and overlapping courses. Create the directory if it is absent.
2. Choose a stable course ID shaped as a readable slug plus six random lowercase hexadecimal characters, such as `linear-algebra-7ac91e`. Never derive links or progress identity from the display title.
3. Plan a short sequence of lessons. Each lesson should teach one coherent idea and take roughly 5–15 minutes.
4. Create `course.json`, one HTML fragment per lesson under `lessons/`, and one matching quiz under `quizzes/`. Start from [assets/course-template](assets/course-template) when useful, but replace all example IDs and content.
5. Give every substantive learning point at least one concrete example. Put examples in the exact collapsible form documented in the format reference.
6. Write 5–7 varied questions per lesson. Include explanations for every question and strong rubrics plus reference answers for free responses.
7. Validate the finished course:

   ```bash
   python3 skills/create-socraites-course/scripts/validate_course.py data/courses/<course-id>
   ```

8. Fix every reported error, then start Socraites and inspect the course as a learner. Do not edit `data/progress/` while authoring.

## Boundaries

- Lesson files are trusted HTML fragments rendered inside Socraites' shared shell. Do not include document wrappers, scripts, stylesheets, forms, or iframes.
- Keep answer keys, rubrics, and reference answers only in quiz JSON. Never place them in learner-visible lesson metadata or frontend code.
- Preserve existing course IDs and lesson IDs when revising content so learner progress remains connected.
- Treat source accuracy separately from formatting. Research or cite authoritative material when the subject requires it; never invent facts or references.
