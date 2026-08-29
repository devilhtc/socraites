# Socraites

Socraites is a local-first learning app for short HTML lessons, retrieval-practice quizzes, saved progress, and optional feedback from a Codex agent over the Agent Client Protocol (ACP).

The application stores courses and learner activity as ordinary local files. Nothing under `data/` is committed, so each installation owns its lessons, answers, feedback, and tutor conversations.

## Features

- A React/Vite lesson player with light and dark themes
- A FastAPI backend with file-backed persistence
- Bite-sized HTML lessons with Mermaid diagrams, syntax-highlighted code, and privacy-enhanced YouTube embeds
- Single-choice, multiple-choice, ordering, and free-response questions
- Refresh-safe drafts, immutable attempts, progress, generated questions, and tutor history
- Deterministic local grading for structured questions
- Optional semantic grading, question generation, tutoring, and chapter editing through Codex ACP
- A bundled authoring skill and validator for creating new courses

## Requirements

- macOS, Linux, or Windows through WSL
- [Node.js](https://nodejs.org/) `20.19+` or `22.12+`
- Python `3.11–3.14`
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Git

Codex is optional. The setup script installs the compatible Codex CLI and ACP adapter locally inside `agent-runtime/`; you do not need a global Codex installation.

## Quick start

```bash
git clone https://github.com/devilhtc/socraites.git
cd socraites
./scripts/setup.sh
./scripts/dev.sh
```

Open <http://127.0.0.1:5173>.

The first launch intentionally has an empty lesson library. `data/courses/` and `data/progress/` are created automatically and remain private to your machine. See [Create a course](#create-a-course) to add content.

The backend listens on `127.0.0.1:8765`; the frontend development server listens on `127.0.0.1:5173`.

## Set up the Codex agent

Socraites works without Codex, but free-response answers then use a clearly labelled lexical rubric preview, and agent-powered tutoring and question generation are unavailable.

To use your existing ChatGPT/Codex login:

1. Install the project dependencies with `./scripts/setup.sh`.
2. Run the project-local Codex CLI once:

   ```bash
   ./agent-runtime/node_modules/.bin/codex
   ```

3. Choose **Sign in with ChatGPT** when prompted, then exit Codex after sign-in completes. This follows the [official Codex CLI sign-in flow](https://learn.chatgpt.com/docs/codex/cli).
4. Start Socraites with the ACP agent required:

   ```bash
   SOCRAITES_JUDGE=codex-acp ./scripts/dev.sh
   ```

5. Confirm the adapter is active:

   ```bash
   curl http://127.0.0.1:8765/api/judge/status
   ```

   The response should contain `"active_mode":"codex-acp"`.

The ACP adapter uses the authentication cached by the local Codex CLI. Grading and question generation run without write access. For an explicit lesson or quiz edit, Socraites gives the tutor temporary copies of only the selected chapter's `lesson.html` and `quiz.json`; it validates both before copying changes into the course. The tutor cannot see learner progress, other chapters, or the rest of the repository through that workspace. Permission escalation, browser access, and network access remain disabled. This is careful local containment, not a hardened multi-user sandbox, so use lesson and answer content you trust. See the [official Codex sandboxing overview](https://learn.chatgpt.com/docs/sandboxing) for the underlying workspace-write model.

### Agent modes

Set `SOCRAITES_JUDGE` when starting the app:

| Value | Behavior |
| --- | --- |
| `auto` | Use Codex ACP when available; otherwise use the local rubric preview. This is the default. |
| `codex-acp` | Require Codex ACP. Agent failures are shown instead of silently falling back. |
| `local` | Stay offline and use the rubric preview for free responses. |

If you prefer API-key authentication, export `OPENAI_API_KEY` before starting Socraites. Never put a key in the repository; `.env` files are ignored.

## Create a course

The repository includes the [`create-socraites-course`](skills/create-socraites-course/SKILL.md) skill. It tells an agent how to generate stable course IDs, lesson manifests, short HTML fragments, diagrams, highlighted code, checked YouTube embeds, collapsible examples, and 5–7 question quizzes in the exact format Socraites accepts.

From Codex or another repository-aware coding agent, ask:

> Read `skills/create-socraites-course/SKILL.md` and create a Socraites course about _your topic_ under `data/courses/`.

`AGENTS.md` also routes course-authoring requests to this skill automatically. The skill includes a copyable template and a standalone validator.

To author manually, copy the template and replace its placeholder content and IDs:

```bash
cp -R skills/create-socraites-course/assets/course-template data/courses/my-topic-a1b2c3
```

Then validate it:

```bash
python3 skills/create-socraites-course/scripts/validate_course.py data/courses/my-topic-a1b2c3
```

Restarting is usually unnecessary during development; the next API request reads current course files.

## Local data layout

```text
data/
├── courses/
│   └── <course-id>/
│       ├── course.json
│       ├── lessons/*.html
│       └── quizzes/*.json
└── progress/
    └── local/<course-id>/
        ├── progress.json
        ├── workspace.json
        ├── attempts/*.json
        ├── interactions/*.json
        ├── generated/<lesson-id>/*.json
        └── tutor/<lesson-id>/*.json
```

`workspace.json` is the refresh-safe working state. Attempts are immutable snapshots containing submitted answers and judge feedback. Browser storage is used only as a short write-ahead cache during the debounce window before a draft reaches FastAPI.

Deleting `data/progress/` resets local learner state. Back up `data/` if you want to preserve courses or progress.

## Development

Run the complete verification suite:

```bash
./scripts/test.sh
```

Or run each part separately:

```bash
(cd backend && uv run pytest)
(cd frontend && npm test)
(cd frontend && npm run build)
```

Project structure:

```text
agent-runtime/   pinned Codex ACP adapter
backend/         FastAPI API, storage, grading, and tutor integration
frontend/        React/Vite interface
scripts/         setup, development, and test entry points
skills/          reusable course-authoring guidance and validation
data/            private courses and learner state; always gitignored
```

## Security notes

- Lesson-authored scripts, forms, objects, and arbitrary frames remain blocked by the Content Security Policy. The only external frame origin is `youtube-nocookie.com`; loading an embedded video contacts YouTube and sends the lesson page's origin as the referrer.
- Quiz answer keys are removed from API responses before they reach the browser.
- Course paths and IDs are validated to prevent escaping the local data directory.
- Tutor-authored edits are staged in a temporary two-file workspace and validated before they replace lesson content.
- The app binds to localhost by default. It is designed as a personal local application, not a hardened multi-user service.
