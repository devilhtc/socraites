import type {
  AttemptResult,
  CourseSummary,
  CourseView,
  JudgeStatus,
  LearningPhase,
  PublicQuiz,
  TutorView,
  WorkspaceView,
} from "./types";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { error?: string };
    throw new Error(payload.error ?? `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export const api = {
  courses(): Promise<CourseSummary[]> {
    return request("/api/courses");
  },
  course(courseId: string): Promise<CourseView> {
    return request(`/api/courses/${encodeURIComponent(courseId)}`);
  },
  quiz(courseId: string, lessonId: string): Promise<PublicQuiz> {
    return request(
      `/api/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/quiz`,
    );
  },
  generateQuestions(courseId: string, lessonId: string): Promise<PublicQuiz> {
    return request(
      `/api/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/questions/generate`,
      { method: "POST" },
    );
  },
  tutor(courseId: string, lessonId: string): Promise<TutorView> {
    return request(
      `/api/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/tutor`,
    );
  },
  sendTutorMessage(courseId: string, lessonId: string, text: string): Promise<TutorView> {
    return request(
      `/api/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/tutor/messages`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      },
    );
  },
  newTutorConversation(courseId: string, lessonId: string): Promise<TutorView> {
    return request(
      `/api/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/tutor/conversations`,
      { method: "POST" },
    );
  },
  activateTutorConversation(courseId: string, lessonId: string, conversationId: string): Promise<TutorView> {
    return request(
      `/api/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/tutor/conversations/${encodeURIComponent(conversationId)}/activate`,
      { method: "POST" },
    );
  },
  submit(
    courseId: string,
    lessonId: string,
    answers: Record<string, unknown>,
  ): Promise<AttemptResult> {
    return request(
      `/api/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/attempts`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers }),
      },
    );
  },
  judgeStatus(): Promise<JudgeStatus> {
    return request("/api/judge/status");
  },
  workspace(courseId: string): Promise<WorkspaceView> {
    return request(`/api/courses/${encodeURIComponent(courseId)}/workspace`);
  },
  navigate(courseId: string, lessonId: string, activePhase: LearningPhase): Promise<WorkspaceView> {
    return request(`/api/courses/${encodeURIComponent(courseId)}/workspace`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active_lesson_id: lessonId, active_phase: activePhase }),
    });
  },
  saveDraft(
    courseId: string,
    lessonId: string,
    answers: Record<string, unknown>,
  ): Promise<WorkspaceView> {
    return request(
      `/api/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/draft`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers }),
      },
    );
  },
};
