# Example courses

These courses are committed demonstrations of Socraites' lesson and quiz formats. They contain no learner progress or credentials.

## GitHub Actions Basics

`github-actions-basics-94b374` is a five-lesson course with 5 to 7 questions per lesson. Its first two lessons demonstrate the richer lesson media:

- `01-event-to-run.html` embeds an official GitHub YouTube video and renders a Mermaid flowchart.
- `02-first-ci-workflow.html` uses syntax highlighting for a complete YAML workflow.

Copy the course into the private local library:

```bash
cp -R examples/courses/github-actions-basics-94b374 data/courses/
```

Then validate it if you are editing the example:

```bash
python3 skills/create-socraites-course/scripts/validate_course.py examples/courses/github-actions-basics-94b374
```
