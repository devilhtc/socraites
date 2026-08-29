import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Socraites API client", () => {
  it("encodes course and lesson identifiers and posts answers as JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          attempt_id: "attempt-1",
          course_id: "acp course",
          lesson_id: "lesson/one",
          created_at: "2026-08-27T00:00:00Z",
          score: 1,
          passed: true,
          results: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.submit("acp course", "lesson/one", { answer: "client" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/courses/acp%20course/lessons/lesson%2Fone/attempts",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ answers: { answer: "client" } }),
      }),
    );
  });

  it("surfaces the backend error message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: "Judge unavailable" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(api.judgeStatus()).rejects.toThrow("Judge unavailable");
  });

  it("saves navigation and draft state through the durable workspace endpoints", async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ course_id: "acp-0fbae9", lessons: {} }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.navigate("acp-0fbae9", "messages", "quiz");
    await api.saveDraft("acp-0fbae9", "messages", { explanation: "still thinking" });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/courses/acp-0fbae9/workspace",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ active_lesson_id: "messages", active_phase: "quiz" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/courses/acp-0fbae9/lessons/messages/draft",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ answers: { explanation: "still thinking" } }),
      }),
    );
  });

  it("requests more questions for the current chapter", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ questions: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.generateQuestions("acp course", "lesson/one");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/courses/acp%20course/lessons/lesson%2Fone/questions/generate",
      { method: "POST" },
    );
  });

  it("uses chapter-scoped tutor conversation endpoints", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(
      new Response(JSON.stringify({ active_conversation_id: null, conversation: null, conversations: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ));
    vi.stubGlobal("fetch", fetchMock);

    await api.tutor("acp course", "lesson/one");
    await api.sendTutorMessage("acp course", "lesson/one", "Explain this");
    await api.newTutorConversation("acp course", "lesson/one");
    await api.activateTutorConversation("acp course", "lesson/one", "conversation one");

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/courses/acp%20course/lessons/lesson%2Fone/tutor", undefined);
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/courses/acp%20course/lessons/lesson%2Fone/tutor/messages",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ text: "Explain this" }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/courses/acp%20course/lessons/lesson%2Fone/tutor/conversations/conversation%20one/activate",
      { method: "POST" },
    );
  });
});
