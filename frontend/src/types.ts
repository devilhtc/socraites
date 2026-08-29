export type LessonRef = {
  id: string;
  title: string;
  summary: string;
  estimated_minutes: number;
  lesson_file: string;
  quiz_file: string;
};

export type CourseConcept = {
  id: string;
  name: string;
  definition: string;
};

export type CourseManifest = {
  schema_version: 1;
  id: string;
  title: string;
  category: string;
  subtitle: string;
  description: string;
  concepts: CourseConcept[];
  lessons: LessonRef[];
};

export type LessonProgress = {
  lesson_id: string;
  attempts: number;
  best_score: number;
  passed: boolean;
  last_attempt_at: string | null;
};

export type CourseProgress = {
  course_id: string;
  learner_id: string;
  updated_at: string | null;
  lessons: Record<string, LessonProgress>;
};

export type CourseView = {
  course: CourseManifest;
  progress: CourseProgress;
};

export type CourseSummary = {
  id: string;
  title: string;
  category: string;
  subtitle: string;
  description: string;
  section_count: number;
  estimated_minutes: number;
  completed_sections: number;
  progress: number;
  last_opened_at: string | null;
};

export type ChoiceOption = { id: string; label: string };
export type FillParagraphBlank = { id: string; options: ChoiceOption[] };

export type PublicQuestion = {
  id: string;
  type: "single_choice" | "multiple_choice" | "ordering" | "fill_paragraph" | "free_response";
  prompt: string;
  points: number;
  options: ChoiceOption[] | null;
  blanks?: FillParagraphBlank[] | null;
};

export type PublicQuiz = {
  id: string;
  title: string;
  passing_score: number;
  questions: PublicQuestion[];
  authored_question_count: number;
  generated_question_count: number;
};

export type QuestionResult = {
  question_id: string;
  score: number;
  earned_points: number;
  possible_points: number;
  verdict: "correct" | "partial" | "incorrect";
  feedback: string;
  explanation: string;
  strengths: string[];
  improvements: string[];
  judge: string;
};

export type AttemptResult = {
  attempt_id: string;
  course_id: string;
  lesson_id: string;
  created_at: string;
  answers: Record<string, unknown>;
  score: number;
  passed: boolean;
  results: QuestionResult[];
};

export type LearningPhase = "lesson" | "quiz";

export type LessonWork = {
  lesson_id: string;
  answers: Record<string, unknown>;
  status: "editing" | "grading" | "graded";
  updated_at: string | null;
  grading_started_at: string | null;
  latest_attempt_id: string | null;
  error: string | null;
  latest_attempt: AttemptResult | null;
};

export type WorkspaceView = {
  schema_version: 1;
  course_id: string;
  learner_id: string;
  active_lesson_id: string;
  active_phase: LearningPhase;
  updated_at: string | null;
  lessons: Record<string, LessonWork>;
};

export type TutorTurn = {
  turn_id: string;
  user_text: string;
  assistant_text: string | null;
  status: "generating" | "completed" | "failed";
  created_at: string;
  updated_at: string;
  error: string | null;
};

export type TutorConversation = {
  schema_version: 1;
  conversation_id: string;
  course_id: string;
  lesson_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  turns: TutorTurn[];
};

export type TutorConversationSummary = {
  conversation_id: string;
  title: string;
  updated_at: string;
  turn_count: number;
};

export type TutorView = {
  active_conversation_id: string | null;
  conversation: TutorConversation | null;
  conversations: TutorConversationSummary[];
};

export type JudgeStatus = {
  configured_mode: string;
  active_mode: string;
  available: boolean;
  detail: string;
};
