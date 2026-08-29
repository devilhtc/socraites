import { describe, expect, it } from "vitest";
import { answersForRetry, nextLessonId } from "./App";
import type { AttemptResult, PublicQuiz } from "./types";

const quiz = {
  id: "messages-quiz",
  title: "Messages",
  passing_score: 0.7,
  authored_question_count: 2,
  generated_question_count: 0,
  questions: [
    {
      id: "shape",
      type: "single_choice",
      prompt: "Which shape?",
      points: 1,
      options: [{ id: "notification", label: "Notification" }],
    },
    {
      id: "order",
      type: "ordering",
      prompt: "Put these in order",
      points: 1,
      options: [
        { id: "request", label: "Request" },
        { id: "response", label: "Response" },
      ],
    },
  ],
} satisfies PublicQuiz;

const attempt = {
  attempt_id: "attempt-1",
  course_id: "acp-0fbae9",
  lesson_id: "messages",
  created_at: "2026-08-28T00:00:00Z",
  answers: {
    shape: "notification",
    order: ["response", "request"],
    explanation: "A notification has no response id.",
  },
  score: 0.8,
  passed: true,
  results: [],
} satisfies AttemptResult;

describe("quiz retries", () => {
  it("starts from the learner's previous inputs", () => {
    expect(answersForRetry(quiz, attempt.answers, attempt)).toEqual(attempt.answers);
  });

  it("can restore saved attempt answers when current state is incomplete", () => {
    expect(answersForRetry(quiz, {}, attempt)).toEqual(attempt.answers);
  });
});

describe("section progression", () => {
  const lessons = [{ id: "boundary" }, { id: "messages" }, { id: "lifecycle" }];

  it("finds the section after the current one", () => {
    expect(nextLessonId(lessons, "messages")).toBe("lifecycle");
  });

  it("returns no next section after the final one", () => {
    expect(nextLessonId(lessons, "lifecycle")).toBeNull();
  });
});
