# Socraites repository guidance

## Course authoring

When asked to create, revise, validate, or explain the format of Socraites lesson or quiz content, read and follow `skills/create-socraites-course/SKILL.md` before editing `data/courses/`.

Treat `data/` as private local state. Never commit its contents. Do not edit learner progress or attempt history unless the user explicitly asks.

## Application changes

Course content uses stable IDs. Preserve existing course and lesson IDs during UI, backend, or content revisions unless the user explicitly requests a migration.

Run `./scripts/test.sh` after application changes. Run the course validator from the authoring skill after changing course files.
