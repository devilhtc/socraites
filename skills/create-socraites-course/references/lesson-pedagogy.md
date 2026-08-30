# Teaching pattern for Socraites lessons

## Research basis

Use these findings as design constraints, not as claims to repeat to the learner:

- New material is easier to interpret when instruction activates relevant prior knowledge. Carnegie Mellon's Eberly Center recommends building from what learners already know and using familiar examples to connect old and new ideas: [Assessing Prior Knowledge](https://www.cmu.edu/teaching/designteach/teach/priorknowledge.html) and [Lectures](https://www.cmu.edu/teaching/designteach/design/instructionalstrategies/lectures.html).
- The U.S. Institute of Education Sciences recommends worked examples, integration of concrete and abstract representations, pre-questions that direct attention, and deep explanatory questions: [Organizing Instruction and Study to Improve Student Learning](https://ies.ed.gov/ncee/wwc/PracticeGuide/1).
- A controlled replication found that pairing abstract concepts with concrete examples improved recognition of new examples. It also warns that jargon feels ordinary to experts while loading novices' working memory: [Micallef and Newton, 2022](https://doi.org/10.1177/00986283211058069).
- Example-based learning transfers better when the learner can connect the example to its underlying principle or compare critical features across examples: [Renkl, 2014](https://doi.org/10.1111/cogs.12086).
- Concrete context can hurt transfer when decorative details hide the shared structure. Keep the situation plausible and lean: [The Cognitive Costs of Context](https://pmc.ncbi.nlm.nih.gov/articles/PMC4665226/).

## Opening sequence

Do not begin a lesson with a compressed definition or taxonomy. Give the learner a reason to need the idea first.

1. **Bridge from the course path.** Except in the first lesson, recall one useful result from the previous lesson and name the next question it leaves open. Use one or two sentences in `<p class="lesson-bridge">`. Do not write a recap paragraph.
2. **Put the learner in a small situation.** Give an actor, a goal, and one constraint or surprise. A developer sees tests drift between laptops. A researcher sees the same sensor pattern arise from different sources. Let the situation do real explanatory work.
3. **Make one observation.** Walk through what happens or ask the learner to predict it. Point out the tension in ordinary language before introducing new jargon.
4. **Name the lesson's payoff.** The lead paragraph tells the learner what principle will resolve the situation. The body then earns that claim.

Use this exact opening structure:

```html
<p class="eyebrow">Lesson 2 · Short label</p>
<p class="lesson-bridge">The last lesson followed an event into one workflow run. Now the workflow needs a real job to perform.</p>
<h1>Turn a local check into repeatable CI.</h1>
<div class="lesson-opening">
  <p>You run the tests before every push, but a teammate forgets and merges a broken change. The command works; the habit does not.</p>
  <p class="lead">Put that same command on a clean runner for every pull request, and the repository can enforce the check consistently.</p>
</div>
```

The first lesson omits `lesson-bridge` and opens directly with a course-orienting situation. Every lesson needs exactly one `lesson-opening` before its first `h2`, with at least two paragraphs inside it. One paragraph must use `class="lead"`.

Vary the prose. Do not start every lesson with "Imagine." Useful openings include:

- a decision the learner must make;
- a walkthrough that produces a surprising observation;
- a familiar failure followed by the question that would prevent it;
- two plausible choices whose consequences differ.

## From case to principle

- Walk through the opening case far enough that the learner can see the problem before naming a formal category.
- State the general principle next, and link important terminology to the course concept index.
- Use a worked example when the learner must follow a procedure or message sequence. Show the meaningful steps and explain why each changes the state.
- Use a contrasting example when the boundary matters. Change one critical feature and explain why the outcome changes.
- Tie each example back to the principle in a sentence. A vivid anecdote without that connection is decoration.
- Use a diagram, video, or code block only when it makes a relationship easier to inspect than prose would.

## Continuity and tone

- Treat the course as one explanation split into lessons. A bridge should sound like the next thought, not a table-of-contents announcement.
- Assume intelligence, not background knowledge. Explain the first use of a term without sounding apologetic or childish.
- Prefer second person when it puts the learner inside a decision. Do not invent a fake personal story or overuse rhetorical questions.
- Keep scenarios short. Include only details that affect the observation or principle.
- Near the end, return briefly to the opening situation or point toward the next unresolved question. The existing concept summary can carry this connection.
