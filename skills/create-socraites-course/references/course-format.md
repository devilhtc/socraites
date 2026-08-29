# Socraites course format

## Directory layout

```text
data/courses/<course-id>/
├── course.json
├── lessons/
│   ├── 01-first-topic.html
│   └── 02-second-topic.html
└── quizzes/
    ├── 01-first-topic.json
    └── 02-second-topic.json
```

`<course-id>` must match `^[a-z][a-z0-9-]*-[a-f0-9]{6}$`: a readable lowercase slug followed by a random six-character hexadecimal suffix. Lesson and question IDs use lowercase letters, digits, and hyphens.

## Course manifest

`course.json` uses schema version 1 and no unrecognized fields:

```json
{
  "schema_version": 1,
  "id": "example-course-a1b2c3",
  "title": "Display title",
  "category": "Subject area",
  "subtitle": "One-line promise",
  "description": "A concise description of what the learner will understand.",
  "lessons": [
    {
      "id": "first-topic",
      "title": "A short section title",
      "summary": "What this section teaches in no more than 280 characters.",
      "estimated_minutes": 8,
      "lesson_file": "lessons/01-first-topic.html",
      "quiz_file": "quizzes/01-first-topic.json"
    }
  ]
}
```

IDs are stable storage keys. Display titles may change; IDs should not.

## Lesson HTML

A lesson is a UTF-8 HTML fragment, not a complete document. Socraites supplies fonts, colors, spacing, light/dark themes, and the outer `<article>`.

Allowed presentation patterns include:

```html
<p class="eyebrow">Lesson 1 · Core idea</p>
<h1>The lesson's teaching headline.</h1>
<p class="lead">A short orientation that explains why the idea matters.</p>

<h2>One learning point</h2>
<p>Explain one idea in plain language before introducing exceptions or terminology.</p>

<div class="concept"><p><strong>Rule:</strong> State a compact rule the learner can retrieve later.</p></div>

<div class="trace">
  <div><b>First interaction</b><br>Only the important detail.</div>
  <div><b>Second interaction</b><br>The resulting state.</div>
</div>

<details><summary>Example: a concrete case</summary><div><p>Show how the learning point behaves in a realistic situation.</p></div></details>
```

The `<details>` and `<summary>` opening tags stay on one line exactly as shown. Put only one line break after `</details>` before the next block.

Quality requirements:

- Fewer than 500 words per lesson fragment.
- One coherent idea per lesson; split dense material into more lessons.
- Every substantive learning point has at least one example.
- At least three `<details><summary>Example: …</summary>` blocks per lesson.
- Prefer important interactions over exhaustive sequences. Use `.trace`, tables, or concise HTML walkthroughs when relationships are clearer visually.
- Use headings, paragraphs, lists, `code`, `pre`, `table`, `.concept`, `.trace`, and collapsible examples. Do not add inline styles.
- Never include `<html>`, `<head>`, `<body>`, `<style>`, `<script>`, `<form>`, or `<iframe>`.

## Quiz JSON

Every lesson has one quiz with 5–7 questions. Use more than one question type when the material supports it. Total points may vary; `passing_score` is a fraction from 0 to 1.

Shared fields for every question:

- `id`: unique stable slug within the quiz.
- `type`: one of `single_choice`, `multiple_choice`, `ordering`, or `free_response`.
- `prompt`: self-contained learner-facing question.
- `points`: a positive number, at most 100.
- `explanation`: what the learner should understand after answering.

### Single choice

```json
{
  "id": "boundary-owner",
  "type": "single_choice",
  "prompt": "Which layer owns the conversation?",
  "points": 1,
  "options": [
    {"id": "client-agent", "label": "The client-agent protocol"},
    {"id": "tool-service", "label": "An unrelated tool service"}
  ],
  "correct_option_ids": ["client-agent"],
  "explanation": "The client-agent protocol owns the conversation boundary."
}
```

Use 2–8 options and exactly one correct option ID.

### Multiple choice

```json
{
  "id": "optional-signals",
  "type": "multiple_choice",
  "prompt": "Which signals are optional?",
  "points": 2,
  "options": [
    {"id": "images", "label": "Image content"},
    {"id": "base", "label": "The base protocol version"},
    {"id": "terminal", "label": "Terminal access"}
  ],
  "correct_option_ids": ["images", "terminal"],
  "explanation": "Optional capabilities must be advertised before use."
}
```

Use 2–10 options. Every correct ID must name an option.

### Ordering

```json
{
  "id": "request-flow",
  "type": "ordering",
  "prompt": "Put the interaction in order.",
  "points": 2,
  "options": [
    {"id": "request", "label": "Client sends a request"},
    {"id": "work", "label": "Agent performs work"},
    {"id": "response", "label": "Agent returns a result"}
  ],
  "correct_order": ["request", "work", "response"],
  "explanation": "The request starts the work and the response completes it."
}
```

Use 2–10 options. `correct_order` must contain every option ID exactly once.

### Free response

```json
{
  "id": "explain-boundary",
  "type": "free_response",
  "prompt": "Explain the distinction in your own words.",
  "points": 3,
  "rubric": "Credit answers that identify both responsibilities and explain why they remain separate.",
  "reference_answer": "The conversation protocol coordinates client-agent exchange; the tool protocol exposes external capabilities to the agent.",
  "explanation": "The protocols cooperate at different boundaries."
}
```

The rubric should describe concepts and reasoning, not demand exact wording. The reference answer must be complete enough for an LLM judge to compare meaning fairly.

## Full quiz envelope

```json
{
  "schema_version": 1,
  "id": "first-topic-quiz",
  "title": "First topic check",
  "passing_score": 0.75,
  "questions": []
}
```

Replace the empty array with 5–7 valid questions. The app strips answer keys, rubrics, and reference answers before sending quiz data to the browser.
