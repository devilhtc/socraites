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
<p class="lead">Name the problem this lesson will help the learner solve.</p>

<h2>One learning point</h2>
<p>Explain one idea in plain language before introducing exceptions or terminology.</p>

<div class="concept"><p><strong>Make the decision explicit.</strong> State the rule the learner can apply later.</p></div>

<div class="trace">
  <div><b>First interaction</b><br>Only the important detail.</div>
  <div><b>Second interaction</b><br>The resulting state.</div>
</div>

<details><summary>Example: a concrete case</summary><div><p>Show how the learning point behaves in a realistic situation.</p></div></details>
```

### Mermaid diagrams

Use a Mermaid diagram when a sequence, state change, hierarchy, or multi-party relationship is materially easier to understand as a picture. Keep it to the important interactions and explain the point in nearby prose. Do not repeat a walkthrough that is already clear in the text.

Write the source in this exact wrapper, with no extra classes or attributes:

```html
<pre class="mermaid">
sequenceDiagram
  participant C as Client
  participant A as Agent
  C->>A: initialize
  A-->>C: version and capabilities
</pre>
```

Socraites renders the block to a theme-aware SVG before placing it in the lesson iframe. No script runs in the lesson. The renderer supports flowcharts, state diagrams, sequence diagrams, class diagrams, entity-relationship diagrams, and XY charts. Prefer flowcharts, state diagrams, and short sequence diagrams for teaching. Keep labels brief, do not add Mermaid initialization directives, and do not put HTML markup inside the block.

The `<details>` and `<summary>` opening tags stay on one line exactly as shown. Put only one line break after `</details>` before the next block.

Quality requirements:

- Fewer than 500 words per lesson fragment.
- One coherent idea per lesson; split dense material into more lessons.
- Every substantive learning point has at least one example.
- At least three `<details><summary>Example: …</summary>` blocks per lesson.
- Prefer important interactions over exhaustive sequences. Use `.trace`, tables, concise HTML walkthroughs, or Mermaid diagrams when relationships are clearer visually.
- Use headings, paragraphs, lists, `code`, `pre`, `table`, `.concept`, `.trace`, and collapsible examples. Do not add inline styles.
- Never include `<html>`, `<head>`, `<body>`, `<style>`, `<script>`, `<form>`, or `<iframe>`.

## Prose and voice

Apply the `unslop` skill when it is available. Use this checklist as the local fallback and as a final audit:

- Write the concrete mechanism, decision, measurement, or consequence. Cut claims that could appear unchanged in an unrelated course.
- Use plain words and active voice. Split any sentence that makes the reader backtrack.
- Remove puffery, promotional copy, filler, vague attribution, generic conclusions, and canned chatbot phrases.
- Avoid stock AI words such as `delve`, `pivotal`, `intricate`, `landscape`, `showcase`, `tapestry`, `underscore`, and `vibrant`.
- Do not force points into groups of three or cycle through synonyms for the same concept.
- Use sentence case headings. Do not decorate headings with emoji.
- Do not use em dashes, en dashes, or curly quotes. Use straight quotes, commas, or separate sentences.
- A bold lead-in may name a rule or concept, but write it as a sentence ending in a period. Avoid labels such as `<strong>Rule:</strong>` or `<strong>Checkpoint:</strong>`.
- Vary sentence length. Let a short sentence carry an important distinction.
- Add human judgment when the subject calls for it, but tie that judgment to a specific fact or tradeoff.

Apply the same prose pass to `course.json` titles, summaries, and descriptions, plus every quiz prompt, option, explanation, rubric, and reference answer. Format correctness does not excuse generic writing.

## Quiz JSON

Every lesson has one quiz with 5 to 7 questions. Use more than one question type when the material supports it. Total points may vary; `passing_score` is a fraction from 0 to 1.

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

Use 2 to 8 options and exactly one correct option ID.

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

Use 2 to 10 options. Every correct ID must name an option.

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

Use 2 to 10 options. `correct_order` must contain every option ID exactly once.

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

Replace the empty array with 5 to 7 valid questions. The app strips answer keys, rubrics, and reference answers before sending quiz data to the browser.
